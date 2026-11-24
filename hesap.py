"""Hesap aracı: şifre unutulursa ya da yeni yönetici gerekirse komut satırından kullanılır.

Çalıştırma:  .venv\\Scripts\\python hesap.py
Şifre ekranda görünmez; yalnızca bu bilgisayarda, uygulamanın kendi veritabanına yazılır.
"""
import getpass
import sys

from app import auth, db

ROLE = {"admin": "Yönetici", "koc": "Koç", "danisan": "Danışan", "kurum": "Kurum yöneticisi"}


def ask_password() -> str:
    while True:
        pw = getpass.getpass("Yeni şifre (en az 8 karakter, ekranda görünmez): ")
        if len(pw) < 8:
            print("  Şifre en az 8 karakter olmalı.")
            continue
        if getpass.getpass("Şifre tekrar: ") != pw:
            print("  Şifreler aynı değil, tekrar deneyin.")
            continue
        return pw


def main() -> None:
    db.init_db()
    users = db.all_rows("SELECT id, email, name, role FROM users WHERE is_demo = 0 ORDER BY id")
    print("\nFarkora hesap aracı\n")
    if users:
        print("Kayıtlı hesaplar:")
        for u in users:
            print(f"  {u['id']:>3}  {u['email']:<40} {ROLE.get(u['role'], u['role'])}  ({u['name']})")
    else:
        print("Henüz hesap yok.")
    print("\n  1) Yeni yönetici hesabı aç")
    print("  2) Bir hesabın şifresini sıfırla")
    print("  0) Çıkış")
    choice = input("\nSeçiminiz: ").strip()

    if choice == "1":
        name = input("Ad soyad: ").strip()
        email = input("E-posta: ").strip().lower()
        if not name or "@" not in email or "." not in email.split("@")[-1]:
            sys.exit("Ad ve geçerli bir e-posta gerekli.")
        if auth.find_by_email(email):
            sys.exit("Bu e-postayla bir hesap zaten var; şifresini sıfırlamak için 2'yi seçin.")
        user = auth.create_user(email, name, "admin", ask_password())
        print(f"\nYönetici hesabı açıldı: {user['email']}. Uygulamada bu e-posta ve şifreyle giriş yapabilirsiniz.")
    elif choice == "2":
        email = input("Şifresi sıfırlanacak hesabın e-postası: ").strip().lower()
        row = auth.find_by_email(email)
        if not row:
            sys.exit("Bu e-postayla bir hesap bulunamadı.")
        auth.set_password(row["id"], ask_password())
        print(f"\nŞifre değiştirildi: {email}. Açık oturumlar kapatıldı; yeni şifreyle giriş yapın.")
    else:
        print("Çıkıldı.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nÇıkıldı.")
