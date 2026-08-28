# app/services/scraper_service.py
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import re
import time


class ScraperService:
    """
    Extrae comentarios de Facebook/Instagram/X usando Playwright o HTML guardado.
    Incluye filtrado de ruido de interfaz y extracción de métricas del post.
    """

    # Textos de interfaz que NUNCA son comentarios (match exacto, normalizado)
    UI_EXACT = {
        "reply", "replies", "like", "likes", "me gusta", "share", "save", "send",
        "follow", "follow back", "unfollow", "report", "delete", "edit", "verified",
        "search", "reels", "messages", "notifications", "profile", "settings",
        "loading", "continue", "help", "press", "jobs", "about", "embed",
        "translate", "see translation", "view replies", "hide replies",
        "add a comment", "post comment", "log in", "sign up", "see more",
        "view more", "copy link", "original audio", "pinned", "subscribe",
        "cancel", "close", "next", "back", "done", "submit", "comment",
        "comments", "others", "responder", "respuesta", "compartir", "guardar",
        "enviar", "seguir", "denunciar", "eliminar", "editar", "verificado",
        "buscar", "mensajes", "notificaciones", "perfil", "configuración",
        "cargando", "continuar", "ayuda", "prensa", "empleos", "acerca de",
        "traducir", "ver traducción", "ver respuestas", "ocultar respuestas",
        "agregar un comentario", "comentar", "publicar", "iniciar sesión",
        "registrate", "registrarte", "ver más", "ver todo", "siguiente",
        "atrás", "listo", "cancelar", "y otros", "otros","ocultar todas las respuestas", "hide all replies",
        "ocultado por instagram", "hidden by instagram",
        "también de meta", "also from meta",
        "información", "information", "threads",
        "crear", "create", "meta",
    }

    # Frases largas de interfaz (match por subcadena)
    UI_SUBSTR = [
        "see more posts", "never miss a post", "sign up for instagram",
        "stay in the loop", "terms of use", "privacy policy", "by continuing",
        "view more comments", "view all comments", "no comments yet",
        "be the first to", "suggested for you", "and others", "more posts",
        "get the app", "download the app", "you agree to", "cookies policy",
        "write a comment", "leave a comment", "meta verified",
        "switch accounts", "create new post", "ver más publicaciones",
        "ver todos los comentarios", "nunca te pierdas", "mantente al tanto",
        "condiciones de uso", "política de privacidad", "al continuar",
        "ver más comentarios", "todavía no hay comentarios", "sé el primero en",
        "sugeridos para ti", "y otras personas", "más publicaciones",
        "obtener la app", "descargá la app", "aceptás las", "cambiar cuenta",
        "crear nueva publicación", "audio original", "fijado por",
        "to like or comment", "instagram lite", "contact uploading",
        "non-users", "instagram from meta", "© 2026 instagram",
        "se limitaron los comentarios", "importación de contactos", "contact importing",
        "y otras personas más", "and other people",
        "ocultado por instagram", "hidden by instagram",
        "también de meta", "from meta", "les gusta a", "liked by",        # Facebook específico
        "seguidores •", "seguidores ·", "seguidos",
        "recomendado por", "opiniones)",
        "compartido con:", "público",
        "contenido de ia", "ai-generated",
        "media.tenor.com", "tenor.com", "giphy.com",
        "villa dolores", "provincia de córdoba",  # ubicaciones sueltas
        "ver más", "see more",  # títulos truncados de posts
    ]

    UI_REGEX = [
        re.compile(r"\band\s*\d+\s*others?\b", re.I),   # "and 2 others" / "and2 others"
        re.compile(r"\by\s*\d+\s+más\b", re.I),         # "y 2 más" / "y2 más"
        re.compile(r"^\d+(\.\d+)?[km]?$", re.I),
        re.compile(r"^\d+\s*(likes?|me gusta|comentarios?|comments?|shares?|views?|reproducciones?|horas?|hours?|d(í|i)as?|days?|min(ute)?s?|sem(ana)?s?|weeks?)$", re.I),
        re.compile(r"^[\W\d_]+$"),  # solo emojis/símbolos/números
        re.compile(r"\by\s*\d+\s*personas?\s*m[aá]s\b", re.I),  # "y 113 personas más"
        re.compile(r"^and\s+[\w.]+(\s+and\s+[\w.]+)?$", re.I),  # "and"
        re.compile(r"^\d[\d.,]*\s*mil\s+seguidores", re.I),  # "433 mil seguidores"
        re.compile(r"recomendado por el \d+%", re.I),
        re.compile(r"…\s*ver más\s*$", re.I),  # "título… Ver más"
        re.compile(r"^https?://\S+$"),  # URL pura
        re.compile(r"^[a-z]+\.[a-z]+\.[a-z]{2,}$", re.I),  # "media.tenor.com"
        re.compile(r"[\u034f\u200b\u200c\u200d\ufeff]{3,}"),     
        re.compile(r"\band\s*\d+\s*others?\b", re.I),
        re.compile(r"\by\s*\d+\s*más\b", re.I),
        re.compile(r"^\d+(\.\d+)?[km]?$", re.I),
        re.compile(r"^[\W\d_]+$"),
        re.compile(r"^\d[\d.,]*\s*mil\s+seguidores", re.I),
        re.compile(r"recomendado por el \d+%", re.I),
        re.compile(r"…\s*ver más\s*$", re.I),
        re.compile(r"^https?://\S+$"),
    ]

    def _es_ruido_facebook(self, comentario: dict) -> bool:
        """Detecta ruido específico de Facebook que pasó los filtros generales."""
        texto = comentario["texto"].strip()
        usuario = comentario["usuario"].strip()
        
        # 1) Nombre duplicado como comentario (ej: "Ramiro Briolotti" como texto Y como usuario)
        if texto.lower() == usuario.lower() and usuario != "Anónimo":
            return True
        
        # 2) Títulos de posts truncados ("… Ver más")
        if re.search(r"…\s*ver más\s*$", texto, re.I) and len(texto) < 150:
            return True
        
        # 3) Usuario detectado como "Facebook" → es metadata, no comentario
        if usuario.lower() == "facebook":
            return True
        
        # 4) Metadata de perfil
        if re.search(r"\d[\d.,]*\s*mil\s+seguidores", texto, re.I):
            return True
        if re.search(r"recomendado por el \d+%", texto, re.I):
            return True
        if "contenido de ia" in texto.lower():
            return True
        
        # 5) Descripciones de accesibilidad de Facebook
        if texto.lower().startswith("puede ser una imagen"):
            return True
        if texto.lower().startswith("puede ser una ilustración"):
            return True
        if "no hay ninguna descripción" in texto.lower():
            return True
        
        # 6) URLs sueltas
        if re.fullmatch(r"https?://\S+", texto):
            return True
        if re.fullmatch(r"[a-z]+\.[a-z]+\.[a-z]{2,}", texto, re.I):
            return True
        
        # 7) Texto con muchos caracteres Unicode invisibles (garbled)
        invisibles = len(re.findall(r"[\u034f\u200b\u200c\u200d\ufeff]", texto))
        if invisibles > 5:
            return True
        
        return False
    
    def _norm(self, texto: str) -> str:
        return " ".join(texto.split())

    def _es_ui(self, texto: str) -> bool:
        """True si el texto es ruido de interfaz, no un comentario."""
        t = self._norm(texto).lower()
        if len(t) < 4:
            return True
        if t in self.UI_EXACT:
            return True
        for frag in self.UI_SUBSTR:
            if frag in t:
                return True
        for rx in self.UI_REGEX:
            if rx.search(t):
                return True
        return False

    # ✅ MÉTODO NUEVO AGREGADO
    def _es_usuario_instagram(self, texto: str) -> bool:
        """True si la línea es SOLO un nombre de usuario (sin espacios)."""
        t = texto.strip()
        if not t or " " in t:
            return False
        if len(t) < 3 or len(t) > 30:
            return False
        return bool(re.fullmatch(r"[a-zA-Z0-9._-]+", t))

    # ✅ MÉTODO NUEVO AGREGADO
    def _limpiar_prefijo_usuario(self, usuario: str) -> str:
        """Saca 'Verified'/'Verificado' pegado al nombre."""
        return re.sub(r"(verified|verificado)$", "", usuario, flags=re.I).strip()

    def _usuario_cercano(self, elem):
        """Busca el nombre de usuario en ancestros cercanos (link de perfil)."""
        parent = elem
        for _ in range(4):
            parent = getattr(parent, "parent", None)
            if parent is None:
                break
            a = parent.find("a", href=lambda h: h and h.startswith("/") and not h.startswith(
                ("/p/", "/reel/", "/reels/", "/explore", "/accounts", "/about", "/legal", "/directory", "/stories")
            ))
            if a:
                nombre = self._norm(a.get_text())
                if nombre and len(nombre) < 40 and not self._es_ui(nombre):
                    return nombre
        return "Anónimo"

    def _usuario_x(self, elem):
        """En X, el nombre visible está en div[data-testid='User-Name']."""
        parent = elem
        for _ in range(5):
            parent = getattr(parent, "parent", None)
            if parent is None:
                break
            uname = parent.find('div', {'data-testid': 'User-Name'})
            if uname:
                nombre = self._norm(uname.get_text()).split("@")[0].strip()
                if nombre and len(nombre) < 40:
                    return nombre
        return "Anónimo"

    def _guardar_html(self, html: str, url: str) -> str | None:
        """Guarda la página completa en la carpeta origen para auditoría/re-proceso."""
        try:
            from flask import current_app
            base = current_app.config["UPLOAD_FOLDER"]
        except Exception:
            base = os.path.join("instance", "uploads")
        carpeta = os.path.join(base, "paginas_origen")
        os.makedirs(carpeta, exist_ok=True)
        nombre = f"pagina_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        path = os.path.join(carpeta, nombre)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"💾 Página origen guardada: {path} (URL: {url})")
            return path
        except Exception as e:
            print(f"⚠️ No se pudo guardar la página origen: {e}")
            return None

    def _extraer_stats(self, soup, red: str = "instagram") -> dict:
        """Extrae métricas de la publicación (likes/comentarios/compartidos)."""
        stats = {"likes": None, "comentarios": None, "compartidos": None}
        texto = soup.get_text(" ")

        def _a_num(valor):
            """'1.234' → 1234 | '...' → None (blindado contra ValueError)."""
            s = re.sub(r"\D", "", str(valor))
            return int(s) if s else None

        def _es_anio(valor) -> bool:
            n = _a_num(valor)
            return n is not None and 1900 <= n <= 2100

        def _valido(valor) -> bool:
            return _a_num(valor) is not None and not _es_anio(valor)

        # ========== FACEBOOK ==========
        if red == "facebook":
            # --- Estrategia 1 (ANCLA): en el HTML guardado, la barra de acciones
            #     aparece como 2-3 números sueltos justo antes de
            #     "Todos los comentarios" / "Comentarios" ---
            textos = soup.find_all(string=True)
            idx_ancla = None
            for i, t in enumerate(textos):
                s = " ".join(t.split())
                if s.startswith("Todos los comentarios") or s == "Comentarios":
                    idx_ancla = i
                    break
            if idx_ancla is not None:
                nums = []
                j = idx_ancla - 1
                while j >= 0 and j > idx_ancla - 60 and len(nums) < 3:
                    s = " ".join(textos[j].split())
                    if re.fullmatch(r"\d[\d.,]*", s):
                        if _valido(s):
                            nums.insert(0, s)
                    elif s and len(s) > 25:
                        break  # texto largo de por medio: ya no es la barra
                    j -= 1
                if len(nums) >= 1:
                    stats["likes"] = nums[0]
                if len(nums) >= 2:
                    stats["comentarios"] = nums[1]
                if len(nums) >= 3:
                    stats["compartidos"] = nums[2]

            # --- Estrategia 2: aria-labels (si la ancla no alcanzó) ---
            if not stats["likes"]:
                for elem in soup.find_all(attrs={"aria-label": True}):
                    m = re.search(r"([\d.,]+)\s*(?:reacciones|me gusta)", elem.get("aria-label") or "", re.I)
                    if m and _valido(m.group(1)):
                        stats["likes"] = m.group(1)
                        break
            if not stats["comentarios"]:
                for elem in soup.find_all(attrs={"aria-label": True}):
                    m = re.search(r"([\d.,]+)\s*comentarios?", elem.get("aria-label") or "", re.I)
                    if m and _valido(m.group(1)):
                        stats["comentarios"] = m.group(1)
                        break
            if not stats["compartidos"]:
                for elem in soup.find_all(attrs={"aria-label": True}):
                    m = re.search(r"([\d.,]+)\s*(?:veces compartido|compartidos|shares)", elem.get("aria-label") or "", re.I)
                    if m and _valido(m.group(1)):
                        stats["compartidos"] = m.group(1)
                        break

            # --- Estrategia 3: patrones de texto ---
            if not stats["comentarios"]:
                m = re.search(r"([\d.,]+)\s*comentarios\b", texto, re.I)
                if m and _valido(m.group(1)):
                    stats["comentarios"] = m.group(1)
            if not stats["compartidos"]:
                m = re.search(r"([\d.,]+)\s*(?:compartidos|veces compartido|shares)\b", texto, re.I)
                if m and _valido(m.group(1)):
                    stats["compartidos"] = m.group(1)
            if not stats["likes"]:
                candidatos = [
                    c for c in re.findall(r"([\d.,]+)\s*(?:me gusta|reacciones|likes)\b", texto, re.I)
                    if _valido(c)
                ]
                if candidatos:
                    stats["likes"] = max(candidatos, key=_a_num)
            return stats

        # ========== INSTAGRAM / X: spans numéricos de la barra de acciones ==========
        nums = []
        for s in soup.find_all("span"):
            t = " ".join(s.get_text().split())
            if not re.fullmatch(r"\d[\d.,]*", t) or s.find("span"):
                continue
            padre = s.parent
            clases = padre.get("class", []) if hasattr(padre, "get") else []
            if "x6s0dn4" in clases:
                nums.append(t)
        if len(nums) >= 1:
            stats["likes"] = nums[0]
        if len(nums) >= 2:
            stats["comentarios"] = nums[1]
        if len(nums) >= 3:
            stats["compartidos"] = nums[2]

        # Fallbacks clásicos (blindados)
        if not stats["likes"]:
            m = re.search(r"les gusta a [\w.]+ y ([\d.,]+) personas m[aá]s", texto, re.I) or \
                re.search(r"liked by [\w.]+ and ([\d.,]+) others", texto, re.I)
            if m and _valido(m.group(1)):
                stats["likes"] = str(_a_num(m.group(1)) + 1)
        if not stats["comentarios"]:
            m = re.search(r"([\d.,]+)\s*(?:comments|comentarios)\b", texto, re.I)
            if m and _valido(m.group(1)):
                stats["comentarios"] = m.group(1)
        if not stats["compartidos"]:
            m = re.search(r"([\d.,]+)\s*(?:shares|reenv[ií]os|veces compartido)", texto, re.I)
            if m and _valido(m.group(1)):
                stats["compartidos"] = m.group(1)
        return stats
    
    def detectar_red_desde_html(self, soup, url: str = "") -> str:
        """Detecta la red desde la URL o, si falta, desde el HTML guardado."""
        u = (url or "").lower()
        if "instagram" in u:
            return "instagram"
        if "x.com" in u or "twitter" in u:
            return "x"
        if "facebook.com" in u:
            return "facebook"
        # Detección por contenido del HTML (meta tags del <head>)
        head = str(soup.head).lower() if soup.head else ""
        if "instagram.com" in head or "instagram from meta" in head:
            return "instagram"
        if "twitter.com" in head or "x.com" in head:
            return "x"
        return "facebook"

    def extraer_de_url(self, url: str) -> dict:
        """Usa Playwright para navegar a la URL y extraer comentarios."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)

                # Intentar expandir comentarios ("Ver más comentarios" / "Load more")
                for _ in range(6):
                    try:
                        boton = page.get_by_text(
                            re.compile(r"ver más comentarios|view more comments|cargar más|load more", re.I)
                        ).first
                        if boton and boton.is_visible():
                            boton.click()
                            time.sleep(2)
                        else:
                            break
                    except Exception:
                        break

                # Un scroll final por si apareció contenido nuevo
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)

                html = page.content()
                browser.close()

                # 💾 Guardar la página completa en la carpeta origen
                self._guardar_html(html, url)

                soup = BeautifulSoup(html, 'html.parser')
                comentarios = self._extraer_comentarios(soup, url)
                # ✅ El primer "comentario" suele ser el caption del autor → lo separamos como contexto
                caption = None
                m_autor = re.search(r"instagram\.com/([a-zA-Z0-9._-]+)/", url)
                autor = m_autor.group(1).lower() if m_autor else None
                if autor and comentarios:
                    primer_user = comentarios[0]["usuario"].lower().replace("verified", "").strip()
                    if primer_user.startswith(autor) or autor.startswith(primer_user):
                        caption = comentarios.pop(0)["texto"]

                url_lower = url.lower()
                red_stats = "instagram" if "instagram.com" in url_lower else ("x" if ("x.com" in url_lower or "twitter.com" in url_lower) else "facebook")
                stats = self._extraer_stats(soup, red_stats)
                if len(comentarios) < 3:
                    return {
                        "success": False,
                        "error_msg": f"Solo se pudieron extraer {len(comentarios)} comentarios. Instagram/Facebook puede estar bloqueando el acceso. Por favor, copiá y pegá los comentarios manualmente."
                    }

                # ✅ Detectar la red real desde la URL
                url_lower = url.lower()
                if "instagram.com" in url_lower:
                    source = "instagram"
                elif "x.com" in url_lower or "twitter.com" in url_lower:
                    source = "x"
                else:
                    source = "facebook"

                data_para_mic = {
                    "post_id": url,
                    "title": "Extracción desde URL",
                    "comments": [
                        {
                            "comment_id": str(i),
                            "user_id": f"user_{i}",
                            "user_name": c.get("usuario", f"Usuario {i}"),
                            "text": c["texto"],
                            "date": datetime.now()
                        }
                        for i, c in enumerate(comentarios)
                    ]
                }
                return {"success": True, "source": source, "data": data_para_mic,
                        "stats": stats, "caption": caption}
        except Exception as e:
            return {
                "success": False,
                "error_msg": f"Error al extraer comentarios: {str(e)}. Por favor, usá el método de copiar y pegar."
            }

    def obtener_html(self, url: str, headless: bool = True) -> str:
        """Devuelve el HTML renderizado de la URL (Playwright headless).
        Lo usa el worker de monitoreo; no toca el flujo blindado de la web."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
            html = page.content()
            browser.close()
        return html
    
    def _extraer_comentarios(self, soup, url: str) -> list:
        """Extrae comentarios del HTML parseado, filtrando ruido de interfaz."""
        comentarios = []
        es_instagram = "instagram.com" in url
        es_facebook = "facebook.com" in url
        es_x = "x.com" in url or "twitter.com" in url

        if es_instagram:
            usuario_pendiente = None
            for span in soup.find_all('span', {'dir': 'auto'}):
                # Procesar solo spans "externos" (evita duplicados anidados)
                padre = span.parent
                anidado = False
                for _ in range(3):
                    if padre is None:
                        break
                    if getattr(padre, "name", None) == "span" and padre.get("dir") == "auto":
                        anidado = True
                        break
                    padre = padre.parent
                if anidado:
                    continue

                texto = self._norm(span.get_text())
                if len(texto) < 3 or self._es_ui(texto):
                    continue

                # 1) Línea que es SOLO un username → queda pendiente para el siguiente
                if self._es_usuario_instagram(texto):
                    usuario_pendiente = texto
                    continue

                # 2) Separar usuario anidado en el mismo span (caption y comentarios)
                usuario = None
                first = span.find(['a', 'span'])
                if first is not None and first is not span:
                    pref = self._norm(first.get_text())
                    if pref and pref != texto and texto.startswith(pref) and len(pref) < 40:
                        usuario = self._limpiar_prefijo_usuario(pref)
                        texto = texto[len(pref):].strip()

                # 3) Sacar timestamp pegado al inicio:
                #    "1wMartín..." / "1 semMartín..." / "2 díasMartín..." / "14 hMartín..."
                texto = re.sub(
                    r"^\d+\s*(?:sem|semana|semanas|w|d|día|días|days?|h|hora|horas|hours?|m|min|minuto|minutos|s|seg|segundo|segundos)\s*",
                    "", texto, flags=re.I
                ).strip()

                if len(texto) < 6 or self._es_ui(texto):
                    continue

                if usuario is None:
                    usuario = usuario_pendiente or self._usuario_cercano(span)
                usuario_pendiente = None
                comentarios.append({"usuario": usuario or "Anónimo", "texto": texto})

        elif es_facebook:
            # Estrategia 1: Buscar divs con estructura de comentario por timestamp
            for div in soup.find_all('div', recursive=True):
                tiempo_span = div.find('span', string=re.compile(
                    r'^\d+\s*(día|días|hora|horas|min|minuto|minutos|sem|semana|h|m|s)$', re.I
                ))
                if not tiempo_span:
                    continue
                
                # Nombre del usuario en span con dir="auto"
                usuario = "Anónimo"
                nombre_span = div.find('span', {'dir': 'auto'})
                if nombre_span:
                    posible_nombre = self._norm(nombre_span.get_text())
                    if 3 < len(posible_nombre) < 50 and not self._es_ui(posible_nombre):
                        if "·" not in posible_nombre and "Responder" not in posible_nombre:
                            usuario = posible_nombre
                
                # Texto del comentario en span con dir="auto" después del tiempo
                texto = ""
                for span in div.find_all('span', {'dir': 'auto'}):
                    posible_texto = self._norm(span.get_text())
                    if (posible_texto == usuario or 
                        self._es_ui(posible_texto) or
                        re.match(r'^\d+\s*(día|días|hora|horas|min|minuto|minutos|sem|semana|h|m|s)$', posible_texto, re.I)):
                        continue
                    if len(posible_texto) > 10:
                        texto = posible_texto
                        break
                
                if texto and len(texto) > 10:
                    comentarios.append({"usuario": usuario, "texto": texto})
            
            # Estrategia 2: Fallback por botón "Responder"
            if len(comentarios) < 5:
                for span in soup.find_all('span', string=re.compile(r'^Responder$', re.I)):
                    padre = span.parent
                    for _ in range(8):
                        if padre is None:
                            break
                        for s in padre.find_all('span', {'dir': 'auto'}):
                            texto = self._norm(s.get_text())
                            if (len(texto) > 15 and 
                                not self._es_ui(texto) and
                                texto != "Responder" and
                                not re.match(r'^\d+\s*(día|días|hora|horas|min)$', texto, re.I)):
                                usuario = "Anónimo"
                                for s2 in padre.find_all('span', {'dir': 'auto'}):
                                    posible = self._norm(s2.get_text())
                                    if (3 < len(posible) < 40 and 
                                        posible != texto and
                                        not self._es_ui(posible) and
                                        "·" not in posible):
                                        usuario = posible
                                        break
                                if not any(c["texto"] == texto for c in comentarios):
                                    comentarios.append({"usuario": usuario, "texto": texto})
                                break
                        padre = padre.parent
            
            # ✅ POST-PROCESAMIENTO: filtrar ruido específico de Facebook
            comentarios = [c for c in comentarios if not self._es_ruido_facebook(c)]
            
        elif es_x:
            for elem in soup.find_all('div', {'data-testid': 'tweetText'}):
                texto = self._norm(elem.get_text())
                if len(texto) < 6 or self._es_ui(texto):
                    continue
                comentarios.append({"usuario": self._usuario_x(elem), "texto": texto})

        # Fallback genérico: cualquier texto con sustancia que parezca comentario
        if len(comentarios) < 3:
            for elem in soup.find_all(['p', 'span']):
                texto = self._norm(elem.get_text())
                # Saltear líneas cortas que suelen ser UI (timestamps, botones)
                if len(texto) < 25 or len(texto) > 500:
                    continue
                if self._es_ui(texto):
                    continue
                # Descartar líneas que son SOLO un timestamp ("14 de agosto", "hace 2 días")
                if re.fullmatch(r"^(hace\s+)?\d+\s*(sem|semana|semanas|día|días|hora|horas|min|minutos|segundos|\w+ de \w+).*$", texto, re.I):
                    continue

        # Eliminar duplicados
        vistos = set()
        comentarios_unicos = []
        for c in comentarios:
            key = c["texto"].lower().strip()
            if key not in vistos and len(key) > 10:
                vistos.add(key)
                comentarios_unicos.append(c)
        return comentarios_unicos