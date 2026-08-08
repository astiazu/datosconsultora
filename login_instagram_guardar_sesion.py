# login_instagram_guardar_sesion.py
"""
Genera la sesión de Instagram que luego se sube al panel.
USAR CON UNA CUENTA SECUNDARIA, NUNCA CON LA CUENTA PRINCIPAL.

El archivo resultante NO es JSON: es un pickle binario codificado en base64,
porque así es como instaloader serializa sus sesiones internamente.

Ejecutar:
    python login_instagram_guardar_sesion.py

Esto genera sesion_instagram.b64.txt que después subís desde:
    /plata/extraccion → "Subir sesión"
"""
import base64
import getpass
import os
import instaloader


def main():
    print("🔐 Generar sesión de Instagram para scraping")
    print("=" * 50)
    print("⚠️  IMPORTANTE: Usar una cuenta SECUNDARIA")
    print("    NUNCA uses tu cuenta principal de Instagram")
    print("=" * 50)

    usuario = input("Usuario de Instagram: ").strip()
    password = getpass.getpass("Contraseña: ")

    print("\n📡 Conectando a Instagram...")
    loader = instaloader.Instaloader()

    try:
        loader.login(usuario, password)
        print("✅ Login exitoso")

        # instaloader guarda la sesión en un archivo pickle binario
        # (aunque el método se llame save_session_to_file con .json)
        archivo_pickle = "sesion_instagram.tmp.pkl"
        loader.save_session_to_file(archivo_pickle)

        # Leer el pickle como binario y codificarlo en base64 para
        # poder guardarlo en un campo Text de la DB sin corrupción
        with open(archivo_pickle, "rb") as f:
            pickle_bytes = f.read()
        os.remove(archivo_pickle)

        b64_texto = base64.b64encode(pickle_bytes).decode("ascii")

        with open("sesion_instagram.b64.txt", "w", encoding="ascii") as f:
            f.write(b64_texto)

        print(f"💾 Sesión guardada en: sesion_instagram.b64.txt")
        print(f"   ({len(b64_texto)} bytes codificados en base64)")
        print("\n🎉 ¡Listo!")
        print("Ahora subí este archivo desde el panel:")
        print("   /plata/extraccion → 'Subir sesión'")

    except instaloader.exceptions.TwoFactorAuthRequiredException:
        print("\n⚠️  Esta cuenta tiene autenticación de dos factores (2FA)")
        codigo_2fa = input("Ingresá el código de 2FA: ").strip()
        try:
            loader.two_factor_login(codigo_2fa)
            print("✅ 2FA verificado")
            archivo_pickle = "sesion_instagram.tmp.pkl"
            loader.save_session_to_file(archivo_pickle)
            with open(archivo_pickle, "rb") as f:
                pickle_bytes = f.read()
            os.remove(archivo_pickle)
            b64_texto = base64.b64encode(pickle_bytes).decode("ascii")
            with open("sesion_instagram.b64.txt", "w", encoding="ascii") as f:
                f.write(b64_texto)
            print(f"💾 Sesión guardada en: sesion_instagram.b64.txt")
            print("\n🎉 ¡Listo!")
        except Exception as e:
            print(f"❌ Error en 2FA: {e}")

    except instaloader.exceptions.BadCredentialsException:
        print("❌ Usuario o contraseña incorrectos")

    except instaloader.exceptions.ConnectionException as e:
        print(f"❌ Error de conexión: {e}")

    except Exception as e:
        print(f"❌ Error inesperado: {e}")


if __name__ == "__main__":
    main()