/* Farkora: masaüstüne / telefona "uygulama olarak yükle" için gereken servis çalışanı.
   Hiçbir şeyi önbelleğe almaz; her istek doğrudan sunucuya gider (veriler hep güncel kalır). */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
