"""Web sunucusu (FastAPI). Çalıştırma: python run.py

Her API ucu oturum açmış bir kullanıcı ister ve rolüne göre yetki kontrolü yapar (bkz. auth.py).
"""
import secrets
import shutil
import uuid
from datetime import date, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import (agent, agents, analysis, auth, db, demo, insights, meetingbot, notify, safety, selfcoach, training,
               video, vision)
from .config import (AGENT_INTERVAL_MIN, COMMITMENT_CHECK_DAYS, LLM_PROVIDER, PUBLIC_BASE_URL, RESEARCH_MODE,
                     TRANSCRIBE_MODE, UPLOAD_DIR)
from .llm import LLMError
from .sources import UploadSource

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop = agent.start_scheduler(AGENT_INTERVAL_MIN) if AGENT_INTERVAL_MIN > 0 else None
    bot_stop = meetingbot.start_poller()
    yield
    bot_stop.set()
    if stop:
        stop.set()


app = FastAPI(title="Farkora", lifespan=lifespan)
db.init_db()
demo.ensure_demo_accounts()
upload_source = UploadSource()


@app.middleware("http")
async def no_cache_static(request, call_next):
    """Arayüz güncellenince tarayıcı eski dosyayı göstermesin."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    return response


# ===================================================================
# Kimlik doğrulama ve yetki
# ===================================================================


def current_user(request: Request) -> dict:
    user = auth.user_from_token(request.cookies.get(auth.COOKIE))
    if not user:
        raise HTTPException(401, "Oturum açmanız gerekiyor.")
    return user


def roles(*allowed: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in allowed:
            raise HTTPException(403, "Bu işlem için yetkiniz yok.")
        return user
    return dep


staff = roles("admin", "koc")
admin_only = roles("admin")


def managed_client(client_id: int, user: dict) -> dict:
    """Koç paneli erişimi: admin veya danışanın koçu."""
    client = db.get_client(client_id)
    if not client:
        raise HTTPException(404, "Danışan bulunamadı.")
    if not auth.can_manage_client(user, client):
        raise HTTPException(403, "Bu danışana erişim yetkiniz yok.")
    return client


def portal_client(client_id: int, user: dict) -> dict:
    """Danışan portalı erişimi: danışanın kendisi, koçu veya admin."""
    client = db.get_client(client_id)
    if not client:
        raise HTTPException(404, "Danışan bulunamadı.")
    if not auth.can_view_client_portal(user, client):
        raise HTTPException(403, "Bu bilgilere erişim yetkiniz yok.")
    return client


def _login(response: Response, user_id: int) -> None:
    response.set_cookie(auth.COOKIE, auth.create_session(user_id), httponly=True, samesite="lax",
                        max_age=auth.SESSION_DAYS * 86400)


class SetupIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class DemoLoginIn(BaseModel):
    role: Literal["admin", "koc", "danisan", "kurum"]


class PasswordIn(BaseModel):
    password: str
    current: str = ""


def _check_password(pw: str) -> None:
    if len(pw) < 8:
        raise HTTPException(400, "Şifre en az 8 karakter olmalı.")


def _check_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Geçerli bir e-posta adresi girin.")
    if auth.find_by_email(email):
        raise HTTPException(400, "Bu e-posta ile kayıtlı bir kullanıcı zaten var.")
    return email


def _self_guided(user: dict | None) -> bool:
    if not user or user["role"] != "danisan" or not user.get("client_id"):
        return False
    c = db.get_client(user["client_id"])
    return bool(c and c.get("self_guided"))


@app.get("/api/auth/state")
def auth_state(request: Request):
    user = auth.user_from_token(request.cookies.get(auth.COOKIE))
    return {
        "user": user and {**user, "role_label": "Bireysel kullanıcı" if _self_guided(user) else auth.ROLE_LABELS[user["role"]],
                          "self_guided": _self_guided(user)},
        "setup_needed": auth.user_count() == 0,
        "demo_roles": demo.demo_roles(),
    }


@app.post("/api/auth/setup")
def auth_setup(body: SetupIn, response: Response):
    """İlk kurulum: ilk yönetici hesabını oluşturur (yalnızca hiç kullanıcı yokken)."""
    if auth.user_count() > 0:
        raise HTTPException(400, "Kurulum zaten tamamlanmış.")
    if not body.name.strip():
        raise HTTPException(400, "Ad soyad boş olamaz.")
    _check_password(body.password)
    user = auth.create_user(_check_email(body.email), body.name, "admin", body.password)
    # Kurulumdan önce oluşturulmuş, koçu olmayan danışanlar ilk yöneticiye atanır
    with db.connect() as conn:
        conn.execute("UPDATE clients SET coach_id = ? WHERE coach_id IS NULL AND name NOT LIKE '%(Örnek)%'", (user["id"],))
    _login(response, user["id"])
    return user


@app.post("/api/auth/login")
def auth_login(body: LoginIn, response: Response):
    row = auth.find_by_email(body.email)
    if not row or not auth.verify_password(body.password, row["password_hash"]):
        raise HTTPException(400, "E-posta veya şifre hatalı.")
    _login(response, row["id"])
    return auth.get_user(row["id"])


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str
    age: int
    kvkk: bool = False
    not_therapy: bool = False


@app.post("/api/auth/register")
def auth_register(body: RegisterIn, response: Response):
    """Koçsuz mod: kullanıcı kendisi kayıt olur (18 yaş ve üstü)."""
    if auth.user_count() == 0:
        raise HTTPException(400, "Önce yönetici kurulumu yapılmalı.")
    name = body.name.strip()[:80]
    if not name:
        raise HTTPException(400, "Adını ya da bir takma ad yaz.")
    if body.age < 18:
        raise HTTPException(400, "Farkora'yı kendi başına kullanmak için 18 yaşında ya da daha büyük olmalısın.")
    if body.age > 110:
        raise HTTPException(400, "Yaşını kontrol eder misin?")
    if not (body.kvkk and body.not_therapy):
        raise HTTPException(400, "Devam etmek için iki onay kutusunu da işaretle.")
    _check_password(body.password)
    email = _check_email(body.email)
    client = db.create_client(name, "", email=email, consent=True, self_guided=1, age=body.age)
    user = auth.create_user(email, name, "danisan", body.password, client_id=client["id"])
    selfcoach.get_or_create(client["id"])
    _login(response, user["id"])
    return user


@app.post("/api/auth/demo-login")
def auth_demo_login(body: DemoLoginIn, response: Response):
    """Sunum kolaylığı: örnek verideki hesaplara şifresiz giriş (yalnızca is_demo hesaplar)."""
    user = demo.demo_user(body.role)
    if not user:
        raise HTTPException(404, "Bu rol için örnek hesap yok. Önce örnek veriyi yükleyin.")
    _login(response, user["id"])
    return user


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    email: str
    code: str
    password: str


@app.post("/api/auth/forgot")
def auth_forgot(body: ForgotIn):
    """Şifremi unuttum: hesabın e-postasına 6 haneli kod gönderir.
    Hesabın var olup olmadığı dışarıya söylenmez. E-posta (SMTP) ayarlı değilse kod, uygulamanın
    çalıştığı bilgisayardaki sunucu penceresine yazılır (yalnızca o bilgisayara erişen görebilir)."""
    row = auth.find_by_email(body.email)
    if row and not row["is_demo"]:
        code = auth.create_reset_code(row["id"])
        if code:
            status, _ = notify.send_email(
                row["email"], "Farkora şifre sıfırlama kodu",
                f"Merhaba {row['name']},\n\nŞifre sıfırlama kodunuz: {code}\n\n"
                f"Kod {auth.RESET_MINUTES} dakika geçerlidir. Bu isteği siz yapmadıysanız bu e-postayı yok sayın.")
            if status != "gonderildi":
                print(f"\n[Farkora] E-posta gönderilemedi ({status}). Şifre sıfırlama kodu: {row['email']} -> {code}\n",
                      flush=True)
    return {"ok": True, "eposta_ayarli": notify.status()["eposta"], "dakika": auth.RESET_MINUTES}


@app.post("/api/auth/reset")
def auth_reset(body: ResetIn, response: Response):
    _check_password(body.password)
    row = auth.find_by_email(body.email)
    if not row or row["is_demo"] or not auth.use_reset_code(row["id"], body.code):
        raise HTTPException(400, "Kod hatalı ya da süresi dolmuş. Yeni kod isteyebilirsiniz.")
    auth.set_password(row["id"], body.password)
    _login(response, row["id"])
    return auth.get_user(row["id"])


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    auth.end_session(request.cookies.get(auth.COOKIE))
    response.delete_cookie(auth.COOKIE)
    return {"ok": True}


@app.post("/api/auth/password")
def auth_change_password(body: PasswordIn, user: dict = Depends(current_user)):
    row = auth.find_by_email(user["email"])
    if not auth.verify_password(body.current, row["password_hash"]):
        raise HTTPException(400, "Mevcut şifre hatalı.")
    _check_password(body.password)
    auth.set_password(user["id"], body.password)
    return {"ok": True}


# ===================================================================
# Kullanıcı yönetimi (yönetici)
# ===================================================================


class UserIn(BaseModel):
    name: str
    email: str
    role: Literal["admin", "koc", "kurum"]
    password: str
    organization_id: int | None = None


@app.get("/api/users")
def users(_: dict = Depends(admin_only)):
    return auth.list_users()


@app.post("/api/users")
def create_user(body: UserIn, _: dict = Depends(admin_only)):
    if not body.name.strip():
        raise HTTPException(400, "Ad soyad boş olamaz.")
    _check_password(body.password)
    if body.role == "kurum" and not (body.organization_id and db.get_organization(body.organization_id)):
        raise HTTPException(400, "Kurum yöneticisi için bir kurum seçin.")
    return auth.create_user(_check_email(body.email), body.name, body.role, body.password,
                            organization_id=body.organization_id if body.role == "kurum" else None)


@app.post("/api/users/{user_id}/password")
def reset_user_password(user_id: int, body: PasswordIn, _: dict = Depends(admin_only)):
    if not auth.get_user(user_id):
        raise HTTPException(404, "Kullanıcı bulunamadı.")
    _check_password(body.password)
    auth.set_password(user_id, body.password)
    return {"ok": True}


class RoleIn(BaseModel):
    role: Literal["admin", "koc", "kurum"]
    organization_id: int | None = None


@app.patch("/api/users/{user_id}")
def change_role(user_id: int, body: RoleIn, me: dict = Depends(admin_only)):
    """Yetki verme: bir hesabı yönetici, koç veya kurum yöneticisi yapar."""
    user = auth.get_user(user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı.")
    if user_id == me["id"]:
        raise HTTPException(400, "Kendi yetkinizi değiştiremezsiniz (başka bir yönetici değiştirebilir).")
    if user["role"] == "danisan":
        raise HTTPException(400, "Danışan girişlerinin yetkisi değiştirilemez; koç ya da yönetici için yeni kullanıcı açın.")
    org_id = body.organization_id if body.role == "kurum" else None
    if body.role == "kurum" and not (org_id and db.get_organization(org_id)):
        raise HTTPException(400, "Kurum yöneticisi için bir kurum seçin.")
    if user["role"] in ("admin", "koc") and body.role == "kurum":
        with db.connect() as conn:  # kurum yöneticisi danışan yönetemez: danışanları koçsuz kalır
            conn.execute("UPDATE clients SET coach_id = NULL WHERE coach_id = ?", (user_id,))
    db._update("users", user_id, {"role": body.role, "organization_id": org_id})
    return auth.get_user(user_id)


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, me: dict = Depends(admin_only)):
    if user_id == me["id"]:
        raise HTTPException(400, "Kendi hesabınızı silemezsiniz.")
    if not auth.get_user(user_id):
        raise HTTPException(404, "Kullanıcı bulunamadı.")
    with db.connect() as conn:  # silinen koçun danışanları koçsuz kalır (yönetici yeniden atar)
        conn.execute("UPDATE clients SET coach_id = NULL WHERE coach_id = ?", (user_id,))
    auth.delete_user(user_id)
    return {"ok": True}


@app.get("/api/coaches")
def coaches(_: dict = Depends(staff)):
    return [u for u in auth.list_users() if u["role"] in ("admin", "koc")]


# ===================================================================
# Genel
# ===================================================================


@app.get("/api/status")
def status(_: dict = Depends(current_user)):
    return {"llm": LLM_PROVIDER, "transcribe": TRANSCRIBE_MODE, "research": RESEARCH_MODE,
            "kanallar": notify.status(), "toplanti_botu": meetingbot.provider()}


@app.get("/api/agents")
def agents_overview(user: dict = Depends(staff)):
    """4 yapay zekâ ajanı: görev tanımları ve çalışma istatistikleri."""
    return {"agents": agents.overview(coach_id=None if user["role"] == "admin" else user["id"]),
            "kanallar": notify.status(), "toplanti_botu": meetingbot.provider()}


@app.get("/api/dashboard")
def dashboard(user: dict = Depends(staff)):
    return insights.dashboard(coach_id=None if user["role"] == "admin" else user["id"])


@app.post("/api/demo/seed")
def demo_seed(_: dict = Depends(admin_only)):
    return demo.seed()


# ===================================================================
# Kurumlar / birimler
# ===================================================================


class OrganizationIn(BaseModel):
    name: str
    org_type: Literal["sirket", "kamu", "sosyal_birim", "universite", "stk"] = "sirket"
    sector: str = ""
    knowledge: str = ""


def _clean_org(body: OrganizationIn) -> dict:
    data = body.model_dump()
    data["name"] = data["name"].strip()
    if not data["name"]:
        raise HTTPException(400, "Kurum adı boş olamaz.")
    return data


def _require_org(org_id: int) -> dict:
    org = db.get_organization(org_id)
    if not org:
        raise HTTPException(404, "Kurum bulunamadı.")
    return org


@app.get("/api/organizations")
def organizations(_: dict = Depends(staff)):
    return db.list_organizations()


@app.post("/api/organizations")
def create_organization(body: OrganizationIn, _: dict = Depends(staff)):
    return db.create_organization(**_clean_org(body))


@app.put("/api/organizations/{org_id}")
def update_organization(org_id: int, body: OrganizationIn, _: dict = Depends(staff)):
    _require_org(org_id)
    return db.update_organization(org_id, **_clean_org(body))


@app.get("/api/organizations/{org_id}")
def organization_detail(org_id: int, user: dict = Depends(staff)):
    _require_org(org_id)
    return insights.organization_overview(org_id, coach_id=None if user["role"] == "admin" else user["id"])


@app.post("/api/organizations/{org_id}/insight")
def organization_insight(org_id: int, user: dict = Depends(staff)):
    _require_org(org_id)
    try:
        return insights.organization_insight(org_id, coach_id=None if user["role"] == "admin" else user["id"]).model_dump()
    except (ValueError, LLMError) as e:
        raise HTTPException(400, str(e)) from e


# --- Kurum yöneticisi: yalnızca kendi kurumunun anonim paneli ---


@app.get("/api/me/organization")
def my_organization(user: dict = Depends(roles("kurum"))):
    return insights.anonymize(insights.organization_overview(user["organization_id"]))


@app.post("/api/me/organization/insight")
def my_organization_insight(user: dict = Depends(roles("kurum"))):
    try:
        return insights.organization_insight(user["organization_id"]).model_dump()
    except (ValueError, LLMError) as e:
        raise HTTPException(400, str(e)) from e


# ===================================================================
# Danışanlar (koç paneli)
# ===================================================================


class ClientIn(BaseModel):
    name: str
    focus_area: str = ""
    email: str = ""
    phone: str = ""
    client_type: Literal["bireysel", "yonetici"] = "bireysel"
    organization_id: int | None = None
    unit: str = ""
    role_title: str = ""
    goals: str = ""
    notes: str = ""
    consent: bool = False
    coach_id: int | None = None
    notify_channels: list[Literal["eposta", "whatsapp"]] = []


def _clean_client(body: ClientIn, user: dict) -> dict:
    data = {k: v.strip() if isinstance(v, str) else v for k, v in body.model_dump().items()}
    data["notify_channels"] = ",".join(dict.fromkeys(data["notify_channels"]))
    if not data["name"]:
        raise HTTPException(400, "Danışan adı boş olamaz.")
    if data["organization_id"] is not None and not db.get_organization(data["organization_id"]):
        raise HTTPException(400, "Seçilen kurum bulunamadı.")
    if user["role"] == "koc":
        data["coach_id"] = user["id"]  # koç danışanı yalnızca kendine atayabilir
    elif data["coach_id"] is not None:
        coach = auth.get_user(data["coach_id"])
        if not coach or coach["role"] not in ("admin", "koc"):
            raise HTTPException(400, "Seçilen koç bulunamadı.")
    return data


@app.get("/api/clients")
def clients(user: dict = Depends(staff)):
    return db.list_clients(coach_id=None if user["role"] == "admin" else user["id"])


@app.post("/api/clients")
def create_client(body: ClientIn, user: dict = Depends(staff)):
    data = _clean_client(body, user)
    data["coach_id"] = data["coach_id"] or user["id"]
    return db.create_client(**data)


@app.put("/api/clients/{client_id}")
def update_client(client_id: int, body: ClientIn, user: dict = Depends(staff)):
    current = managed_client(client_id, user)
    data = _clean_client(body, user)
    if user["role"] == "admin" and data["coach_id"] is None:
        data["coach_id"] = current.get("coach_id")
    return db.update_client(client_id, **data)


@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int, user: dict = Depends(staff)):
    """Danışanı ve tüm verisini (seanslar, kayıtlar, eğitimler, planlar, giriş hesabı) kalıcı olarak siler.
    Yönetici her danışanı, koç yalnızca kendi danışanını silebilir."""
    managed_client(client_id, user)
    for f in db.delete_client(client_id):
        if f.startswith("kareler:"):
            shutil.rmtree(video.frame_dir(int(f.split(":")[1])), ignore_errors=True)
        else:
            Path(f).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/clients/{client_id}")
def client_detail(client_id: int, user: dict = Depends(staff)):
    client = managed_client(client_id, user)
    return {**client, "sessions": db.list_sessions(client_id), "account": auth.user_for_client(client_id),
            "self": selfcoach.coach_view(client_id) if client.get("self_guided") else None}


# --- Danışanın portal hesabı ---


class AccountIn(BaseModel):
    email: str
    password: str


@app.post("/api/clients/{client_id}/account")
def create_client_account(client_id: int, body: AccountIn, user: dict = Depends(staff)):
    client = managed_client(client_id, user)
    if auth.user_for_client(client_id):
        raise HTTPException(400, "Bu danışanın zaten bir giriş hesabı var.")
    _check_password(body.password)
    return auth.create_user(_check_email(body.email), client["name"], "danisan", body.password, client_id=client_id)


@app.post("/api/clients/{client_id}/account/password")
def reset_client_password(client_id: int, body: PasswordIn, user: dict = Depends(staff)):
    managed_client(client_id, user)
    account = auth.user_for_client(client_id)
    if not account:
        raise HTTPException(404, "Bu danışanın giriş hesabı yok.")
    _check_password(body.password)
    auth.set_password(account["id"], body.password)
    return {"ok": True}


def _require_consent(client: dict) -> None:
    if not client.get("consent"):
        raise HTTPException(
            400, "Bu danışan için KVKK açık rızası kayıtlı değil. Önce danışan bilgilerinden rızayı işaretleyin."
        )


# ===================================================================
# Seanslar
# ===================================================================


@app.post("/api/clients/{client_id}/sessions")
def upload_session(client_id: int, background: BackgroundTasks, file: UploadFile = File(...),
                   title: str = Form(""), user: dict = Depends(staff)):
    _require_consent(managed_client(client_id, user))
    try:
        path = upload_source.save(file.filename or "", file.file)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    session = db.create_session(client_id, title.strip() or file.filename, str(path), upload_source.name)
    background.add_task(analysis.process_session, session["id"])
    return session


class TextSessionIn(BaseModel):
    title: str = ""
    text: str


@app.post("/api/clients/{client_id}/sessions/text")
def upload_text_session(client_id: int, body: TextSessionIn, background: BackgroundTasks,
                        user: dict = Depends(staff)):
    """Yazılı koçluk görüşmesi: mesajlaşma dökümü veya yazılı transkript."""
    _require_consent(managed_client(client_id, user))
    text = body.text.strip()
    if len(text) < 40:
        raise HTTPException(400, "Metin çok kısa. Görüşmenin tamamını yapıştırın.")
    if len(text) > 200_000:
        raise HTTPException(400, "Metin çok uzun (en fazla 200.000 karakter).")
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}.txt"
    path.write_text(text, encoding="utf-8")
    session = db.create_session(client_id, body.title.strip() or "Yazılı seans", str(path), "metin")
    background.add_task(analysis.process_session, session["id"])
    return session


@app.post("/api/clients/{client_id}/sessions/photos")
def upload_photo_session(client_id: int, background: BackgroundTasks, files: list[UploadFile] = File(...),
                         title: str = Form(""), notes: str = Form(""), user: dict = Depends(staff)):
    """Görsel seans (fotoğraf): beyaz tahta, not, çizim, hedef panosu fotoğrafları + koçun kısa notu."""
    _require_consent(managed_client(client_id, user))
    files = [f for f in files if f.filename]
    if not files:
        raise HTTPException(400, "En az bir fotoğraf seçin.")
    if len(files) > video.MAX_PHOTOS:
        raise HTTPException(400, f"En fazla {video.MAX_PHOTOS} fotoğraf yükleyebilirsiniz.")
    if len(notes) > 20_000:
        raise HTTPException(400, "Not çok uzun (en fazla 20.000 karakter).")
    staging = UPLOAD_DIR / f"foto_{uuid.uuid4().hex}"
    try:
        for i, f in enumerate(files):
            ext = Path(f.filename).suffix.lower()
            if ext not in video.PHOTO_EXTENSIONS:
                raise HTTPException(400, f"Desteklenmeyen fotoğraf türü: {ext or '(uzantı yok)'} "
                                         f"(izin verilenler: {', '.join(sorted(video.PHOTO_EXTENSIONS))})")
            raw = staging / f"ham{ext}"
            staging.mkdir(parents=True, exist_ok=True)
            with raw.open("wb") as out:
                shutil.copyfileobj(f.file, out)
            ok = video.save_photo(raw, staging / f"{i}.jpg")
            raw.unlink(missing_ok=True)
            if not ok:
                raise HTTPException(400, f"“{f.filename}” okunamadı; JPG veya PNG deneyin.")
        notes_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.txt"
        notes_path.write_text(notes.strip(), encoding="utf-8")
        session = db.create_session(client_id, title.strip() or "Fotoğraflı seans", str(notes_path), "foto")
        staging.rename(video.frame_dir(session["id"]))
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    background.add_task(analysis.process_session, session["id"])
    return session


def _managed_session(session_id: int, user: dict) -> dict:
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Seans bulunamadı.")
    managed_client(session["client_id"], user)
    return session


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: int, user: dict = Depends(staff)):
    session = _managed_session(session_id, user)
    session.pop("audio_path", None)
    return session


@app.get("/api/sessions/{session_id}/frames/{n}")
def session_frame(session_id: int, n: int, user: dict = Depends(staff)):
    """Video seansından alınan kare (görsel analiz)."""
    _managed_session(session_id, user)
    path = video.frame_dir(session_id) / f"{n}.jpg"
    if not path.exists():
        raise HTTPException(404, "Kare bulunamadı.")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/api/sessions/{session_id}/retry")
def retry_session(session_id: int, background: BackgroundTasks, user: dict = Depends(staff)):
    _managed_session(session_id, user)
    background.add_task(analysis.process_session, session_id)
    return {"ok": True}


@app.post("/api/clients/{client_id}/brief")
def brief(client_id: int, user: dict = Depends(staff)):
    managed_client(client_id, user)
    try:
        return analysis.make_brief(client_id).model_dump()
    except (ValueError, LLMError) as e:
        raise HTTPException(400, str(e)) from e


# ===================================================================
# Eğitimler
# ===================================================================


class TrainingIn(BaseModel):
    area_index: int


@app.post("/api/sessions/{session_id}/trainings")
def create_training(session_id: int, body: TrainingIn, background: BackgroundTasks, user: dict = Depends(staff)):
    session = _managed_session(session_id, user)
    areas = (session["report"] or {}).get("gelisim_alanlari", [])
    if not 0 <= body.area_index < len(areas):
        raise HTTPException(400, "Bu seansta böyle bir gelişim alanı yok.")
    t = db.create_training(session["client_id"], session_id, areas[body.area_index])
    background.add_task(training.generate_training, t["id"])
    return t


@app.get("/api/clients/{client_id}/trainings")
def client_trainings(client_id: int, user: dict = Depends(staff)):
    managed_client(client_id, user)
    return db.list_trainings(client_id)


@app.get("/api/trainings/{training_id}")
def training_detail(training_id: int, user: dict = Depends(current_user)):
    t = db.get_training(training_id)
    if not t:
        raise HTTPException(404, "Eğitim içeriği bulunamadı.")
    portal_client(t["client_id"], user)
    if user["role"] == "danisan" and t["status"] != "tamamlandi":
        raise HTTPException(404, "Eğitim içeriği henüz hazır değil.")
    if user["role"] == "danisan" and t.get("content"):
        t["content"].pop("koc_ozeti", None)
    t["commitments"] = [k for k in db.list_commitments(t["client_id"]) if k["training_id"] == t["id"]]
    return t


# ===================================================================
# Davranış döngüsü: eğer–o zaman planı -> öz-bildirim -> paydaş gözlemi
# ===================================================================


class CommitmentIn(BaseModel):
    durum: str
    davranis: str


class CommitmentResponseIn(BaseModel):
    status: Literal["yapildi", "kismen", "firsat_olmadi", "yapilamadi"]
    reflection: str = ""


class ObserverIn(BaseModel):
    observer_name: str
    relation: str = ""
    consent: bool = False  # koç oluşturuyorsa: danışanın onayı alındı mı


class ObservationIn(BaseModel):
    rating: int
    example: str = ""


def _plan_text(text: str, label: str) -> str:
    text = text.strip()
    if not 3 <= len(text) <= 200:
        raise HTTPException(400, f"{label} 3-200 karakter olmalı.")
    return text


@app.post("/api/trainings/{training_id}/commitment")
def create_commitment(training_id: int, body: CommitmentIn, user: dict = Depends(current_user)):
    t = db.get_training(training_id)
    if not t:
        raise HTTPException(404, "Eğitim bulunamadı.")
    portal_client(t["client_id"], user)
    check = (date.today() + timedelta(days=COMMITMENT_CHECK_DAYS)).isoformat()
    return db.create_commitment(t["client_id"], training_id, _plan_text(body.durum, "Durum"),
                                _plan_text(body.davranis, "Davranış"), check)


def _commitment(commitment_id: int, user: dict) -> dict:
    k = db.get_commitment(commitment_id)
    if not k:
        raise HTTPException(404, "Plan bulunamadı.")
    portal_client(k["client_id"], user)
    return k


@app.post("/api/commitments/{commitment_id}/response")
def respond_commitment(commitment_id: int, body: CommitmentResponseIn, user: dict = Depends(current_user)):
    _commitment(commitment_id, user)
    db.respond_commitment(commitment_id, body.status, body.reflection.strip()[:1000])
    return db.get_commitment(commitment_id)


@app.post("/api/commitments/{commitment_id}/observer")
def create_observer(commitment_id: int, body: ObserverIn, user: dict = Depends(current_user)):
    k = _commitment(commitment_id, user)
    if user["role"] != "danisan" and not body.consent:
        raise HTTPException(400, "Gözlemci eklemek için danışanın onayını alıp kutuyu işaretleyin.")
    name = body.observer_name.strip()[:80]
    if not name:
        raise HTTPException(400, "Gözlemcinin adını yazın.")
    obs = db.create_observation(k["client_id"], k["id"], secrets.token_urlsafe(16), name, body.relation.strip()[:80])
    return {**obs, "link": f"{PUBLIC_BASE_URL}/#/gozlem/{obs['token']}"}


@app.get("/api/observe/{token}")
def observe_info(token: str):
    """Gözlemci sayfası (giriş gerekmez). Yalnızca danışanın adı ve denediği davranış gösterilir."""
    o = db.observation_by_token(token)
    if not o:
        raise HTTPException(404, "Bu bağlantı geçersiz.")
    k = db.get_commitment(o["commitment_id"]) if o["commitment_id"] else None
    first = (db.get_client(o["client_id"])["name"] or "").split()[0]
    return {"danisan": first, "davranis": k["davranis"] if k else "", "durum": k["durum"] if k else "",
            "gozlemci": o["observer_name"], "yanitlandi": o["status"] == "yanitlandi"}


@app.post("/api/observe/{token}")
def observe_answer(token: str, body: ObservationIn):
    o = db.observation_by_token(token)
    if not o:
        raise HTTPException(404, "Bu bağlantı geçersiz.")
    if o["status"] == "yanitlandi":
        raise HTTPException(400, "Bu gözlem zaten yanıtlandı. Teşekkürler!")
    if not 0 <= body.rating <= 3:
        raise HTTPException(400, "Geçersiz seçim.")
    db.answer_observation(o["id"], body.rating, body.example.strip()[:500])
    return {"ok": True}


@app.get("/api/clients/{client_id}/evidence")
def client_evidence(client_id: int, user: dict = Depends(staff)):
    """Davranış kanıtı: öz-bildirim + paydaş gözlemi + sonraki seanstaki bahis."""
    managed_client(client_id, user)
    reviews = []
    for s in db.completed_sessions(client_id):
        for r in (s["report"] or {}).get("plan_degerlendirmesi", []):
            reviews.append({**r, "seans": s["title"], "session_id": s["id"]})
    return {
        "commitments": db.list_commitments(client_id),
        "observations": db.list_observations(client_id),
        "session_reviews": reviews,
        "summary": agent.behavior_evidence(client_id),
        "scale": agent.OBS_SCALE,
        "notifications": db.list_notifications(client_id, 20),
    }


# ===================================================================
# Toplantı botu (Zoom / Teams / Meet)
# ===================================================================


class MeetingBotIn(BaseModel):
    meeting_url: str
    title: str = ""


@app.post("/api/clients/{client_id}/meeting-bot")
def send_meeting_bot(client_id: int, body: MeetingBotIn, user: dict = Depends(staff)):
    _require_consent(managed_client(client_id, user))
    if not meetingbot.valid_url(body.meeting_url):
        raise HTTPException(400, "Geçerli bir Zoom, Teams veya Google Meet toplantı bağlantısı yapıştırın.")
    title = body.title.strip() or f"Toplantı · {date.today().strftime('%d.%m.%Y')}"
    if meetingbot.provider() == "simulasyon":
        title = f"(Simülasyon) {title}"
    return meetingbot.send_bot(client_id, body.meeting_url, title)


@app.get("/api/clients/{client_id}/meeting-bots")
def meeting_bots(client_id: int, user: dict = Depends(staff)):
    managed_client(client_id, user)
    return db.list_meeting_bots(client_id)


@app.post("/api/trainings/{training_id}/retry")
def retry_training(training_id: int, background: BackgroundTasks, user: dict = Depends(staff)):
    t = db.get_training(training_id)
    if not t:
        raise HTTPException(404, "Eğitim içeriği bulunamadı.")
    managed_client(t["client_id"], user)
    background.add_task(training.generate_training, training_id)
    return {"ok": True}


# ===================================================================
# Aktif ajan, görevler, check-in
# ===================================================================


class CheckinIn(BaseModel):
    mood: int
    note: str = ""


class TaskUpdateIn(BaseModel):
    status: Literal["acik", "yapildi", "yapilmadi"]


@app.get("/api/clients/{client_id}/agent")
def agent_overview(client_id: int, user: dict = Depends(staff)):
    managed_client(client_id, user)
    return {
        "actions": db.list_agent_actions(client_id),
        "tasks": db.list_tasks(client_id),
        "checkins": db.list_checkins(client_id),
        "behavior": agent.behavior_metrics(client_id),
        "interval_min": AGENT_INTERVAL_MIN,
    }


@app.post("/api/clients/{client_id}/agent/run")
def agent_run(client_id: int, user: dict = Depends(staff)):
    managed_client(client_id, user)
    try:
        return {"done": agent.run_for_client(client_id)}
    except LLMError as e:
        raise HTTPException(400, str(e)) from e


def _checkin(client_id: int, body: CheckinIn, background: BackgroundTasks) -> dict:
    if not 1 <= body.mood <= 5:
        raise HTTPException(400, "Ruh hali 1 ile 5 arasında olmalı.")
    checkin = db.create_checkin(client_id, body.mood, body.note.strip())
    client = db.get_client(client_id)
    if client.get("self_guided") and safety.is_crisis(body.note):
        p = selfcoach.get_or_create(client_id)
        selfcoach._enter_crisis(client_id, p["phase"] if p["phase"] != "kriz" else "aktif")
    background.add_task(agent.run_safely, client_id)  # ruh hali düştüyse ajan koçu uyarır
    return checkin


@app.post("/api/clients/{client_id}/checkins")
def create_checkin(client_id: int, body: CheckinIn, background: BackgroundTasks, user: dict = Depends(current_user)):
    portal_client(client_id, user)
    return _checkin(client_id, body, background)


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdateIn, user: dict = Depends(current_user)):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Görev bulunamadı.")
    portal_client(task["client_id"], user)
    db.update_task(task_id, body.status)
    return db.get_task(task_id)


# ===================================================================
# Danışan: kendi gelişim portalı
# ===================================================================


@app.get("/api/clients/{client_id}/portal")
def client_portal(client_id: int, user: dict = Depends(current_user)):
    """Danışanın göreceği veri (koç da önizleme için açabilir). ICF ve transkript içermez."""
    portal_client(client_id, user)
    return insights.client_progress(client_id)


@app.get("/api/me/portal")
def my_portal(user: dict = Depends(roles("danisan"))):
    return insights.client_progress(user["client_id"])


@app.post("/api/me/checkins")
def my_checkin(body: CheckinIn, background: BackgroundTasks, user: dict = Depends(roles("danisan"))):
    return _checkin(user["client_id"], body, background)


# ===================================================================
# Koçsuz mod (kendi kendine koçluk)
# ===================================================================


def self_user(user: dict = Depends(roles("danisan"))) -> dict:
    if not _self_guided(user):
        raise HTTPException(403, "Bu bölüm kendi başına kullanan hesaplar içindir.")
    return user


class IntakeIn(BaseModel):
    meslek: str = ""
    yer: Literal["", "buyuksehir", "sehir", "ilce", "koy"] = ""
    yasam: Literal["", "yalniz", "aile", "partner", "arkadas", "yurt"] = ""
    hobiler: list[str] = []
    ortamlar: list[str] = []
    sevdikleri: str = ""
    renkler: str = ""
    zaman: Literal["", "az", "orta", "cok"] = ""
    butce: Literal["", "yok", "az", "rahat"] = ""
    kisit: str = ""
    konu: str = "diger"
    sorun: str


class SelfStartIn(BaseModel):
    intake: IntakeIn
    tipi: list[int]


class SelfTextIn(BaseModel):
    text: str = ""


_LABELS = {
    "yer": {"buyuksehir": "büyükşehir", "sehir": "şehir", "ilce": "ilçe / kasaba", "koy": "köy"},
    "yasam": {"yalniz": "yalnız", "aile": "ailesiyle", "partner": "eşi / partneriyle", "arkadas": "ev arkadaşıyla", "yurt": "yurtta"},
    "zaman": {"az": "haftada 1-2 saat", "orta": "haftada 3-5 saat", "cok": "haftada 5 saatten fazla"},
    "butce": {"yok": "ücretsiz etkinlikler", "az": "az bir bütçe", "rahat": "bütçe sorun değil"},
}


@app.get("/api/me/self")
def self_state(user: dict = Depends(self_user)):
    return selfcoach.state(user["client_id"])


@app.post("/api/me/self/start")
def self_start(body: SelfStartIn, user: dict = Depends(self_user)):
    intake = body.intake.model_dump()
    intake["sorun"] = intake["sorun"].strip()[:3000]
    if len(intake["sorun"]) < 10:
        raise HTTPException(400, "Konunu biraz daha anlatır mısın? (en az birkaç kelime)")
    if intake["konu"] not in selfcoach.TOPICS:
        intake["konu"] = "diger"
    intake["hobiler"] = [h.strip()[:40] for h in intake["hobiler"] if h.strip()][:15]
    intake["ortamlar"] = [h.strip()[:40] for h in intake["ortamlar"] if h.strip()][:10]
    for k in ("meslek", "sevdikleri", "renkler", "kisit"):
        intake[k] = intake[k].strip()[:300]
    for k, labels in _LABELS.items():  # yapay zekâ için okunur değer
        intake[k] = labels.get(intake[k], intake[k])
    try:
        return selfcoach.start(user["client_id"], intake, body.tipi)
    except (ValueError, LLMError) as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/me/self/chat")
def self_chat(body: SelfTextIn, user: dict = Depends(self_user)):
    try:
        return selfcoach.chat(user["client_id"], body.text)
    except (ValueError, LLMError) as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/me/self/correct")
def self_correct(body: SelfTextIn, user: dict = Depends(self_user)):
    if len(body.text.strip()) < 3:
        raise HTTPException(400, "Neyi düzeltmek istediğini yaz.")
    try:
        selfcoach.build_profile(user["client_id"], correction=body.text.strip()[:1000])
    except LLMError as e:
        raise HTTPException(400, str(e)) from e
    return selfcoach.state(user["client_id"])


@app.post("/api/me/self/confirm")
def self_confirm(background: BackgroundTasks, user: dict = Depends(self_user)):
    try:
        selfcoach.confirm_profile(user["client_id"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    background.add_task(selfcoach.generate_plan, user["client_id"])
    return selfcoach.state(user["client_id"])


@app.post("/api/me/self/resume")
def self_resume(user: dict = Depends(self_user)):
    try:
        selfcoach.resume_after_crisis(user["client_id"])
    except LLMError as e:
        raise HTTPException(400, str(e)) from e
    return selfcoach.state(user["client_id"])


@app.post("/api/me/self/restart")
def self_restart(user: dict = Depends(self_user)):
    """Kendini tanıtma adımlarını baştan yapmak (plan başlamadan önce)."""
    p = selfcoach.get_or_create(user["client_id"])
    if p["phase"] in ("aktif", "plan_hazirlaniyor"):
        raise HTTPException(400, "Planın başladı; baştan başlamak yerine asistanınla konuşabilirsin.")
    db.update_self_profile(user["client_id"], phase="form", questions_asked=0, profile=None)
    return selfcoach.state(user["client_id"])


@app.post("/api/me/self/tasks/{task_id}/swap")
def self_swap_task(task_id: int, body: SelfTextIn, user: dict = Depends(self_user)):
    try:
        return selfcoach.swap_task(user["client_id"], task_id, body.text)
    except (ValueError, LLMError) as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/me/self/coach")
def self_coach_request(user: dict = Depends(self_user)):
    selfcoach.request_coach(user["client_id"])
    return selfcoach.state(user["client_id"])


@app.get("/api/self-guided/requests")
def self_guided_requests(_: dict = Depends(admin_only)):
    return db.self_guided_requests()


# ===================================================================
# Görsel analiz
# ===================================================================


@app.get("/api/clients/{client_id}/images")
def client_images(client_id: int, user: dict = Depends(staff)):
    managed_client(client_id, user)
    return [{k: v for k, v in i.items() if k != "path"} for i in db.list_images(client_id)]


@app.post("/api/clients/{client_id}/images")
def upload_image(client_id: int, background: BackgroundTasks, file: UploadFile = File(...),
                 note: str = Form(""), user: dict = Depends(staff)):
    _require_consent(managed_client(client_id, user))
    if file.content_type not in vision.ALLOWED_MIME:
        raise HTTPException(400, "Yalnızca PNG, JPEG, WEBP veya GIF görseller yüklenebilir.")
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}[file.content_type]
    data = file.file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "Görsel en fazla 8 MB olabilir.")
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)
    img = db.create_image(client_id, str(path), file.content_type, note.strip())
    background.add_task(vision.analyze_image, img["id"])
    return {k: v for k, v in img.items() if k != "path"}


@app.get("/api/images/{image_id}/file")
def image_file(image_id: int, user: dict = Depends(staff)):
    img = db.get_image(image_id)
    if not img:
        raise HTTPException(404, "Görsel bulunamadı.")
    managed_client(img["client_id"], user)
    return FileResponse(img["path"], media_type=img["mime"])


# ===================================================================
# Arayüz
# ===================================================================


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.webmanifest")
def manifest():
    """Siteyi masaüstüne / telefona uygulama olarak yüklemek için."""
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    # Kök adresten sunulur ki tüm siteyi kapsasın
    return FileResponse(STATIC_DIR / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
