import os
import pathlib
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ENV = pathlib.Path(__file__).resolve().parent.parent / ".env"

def load_env(path=ENV):

    if not path.exists():
        return {}
    vals = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        vals[k] = v
        os.environ.setdefault(k, v)
    return vals

def check(to_email=None, send_probe=False):
    env = load_env()
    server = env.get("MAIL_SERVER", "")
    port = int(env.get("MAIL_PORT", "587") or 587)
    use_tls = str(env.get("MAIL_USE_TLS", "true")).lower() in ("1", "true", "yes")
    user = env.get("MAIL_USERNAME", "")
    pwd = env.get("MAIL_PASSWORD", "")

    print("=" * 60)
    print("KIEM TRA CAU HINH GMAIL SMTP")
    print("=" * 60)
    print(f"  MAIL_SERVER       : {server}:{port} (TLS={use_tls})")
    print(f"  MAIL_USERNAME     : {user}")
    print(f"  MAIL_PASSWORD     : {'<co, ' + str(len(pwd)) + ' ky tu>' if pwd else '<CHUA CAU HINH>'}")
    print(f"  MAIL_DEFAULT_SENDER: {env.get('MAIL_DEFAULT_SENDER', user)}")
    print()

    if not user or not pwd or pwd == "CHUA_CAU_HINH_APP_PASSWORD":
        print("!! Thieu MAIL_USERNAME hoac MAIL_PASSWORD.")
        print("   Hay dat App Password cua Gmail vao .env roi chay lai.")
        return False

    try:
        with smtplib.SMTP(server, port, timeout=20) as s:
            s.ehlo()
            if use_tls:
                s.starttls()
                s.ehlo()
            s.login(user, pwd)
        print("OK  - Ket noi SMTP thanh cong, xac thuc mat khau thanh cong.")
    except smtplib.SMTPAuthenticationError as e:
        print(f"FAIL - Xac thuc that bai (code {e.smtp_code}): {e.smtp_error.decode()[:160]}")
        print("   -> App Password sai, hoac tai khoan chua bat 2-Step Verification.")
        print("   -> Tao tai: https://myaccount.google.com/apppasswords")
        return False
    except smtplib.SMTPServerDisconnected:
        print("FAIL - Gmail cat ket noi ngay khi xac thuc (SMTPServerDisconnected).")
        print("   -> Nguyen nhan thuong gap: tai khoan CHUA bat 2-Step Verification,")
        print("      nen khong the tao App Password.")
        print("   -> Buoc 1: bat 2FA tai https://myaccount.google.com/security")
        print("   -> Buoc 2: tao App Password tai https://myaccount.google.com/apppasswords")
        print("   -> Buoc 3: dan 16 ky tu vao MAIL_PASSWORD trong .env roi chay lai script nay")
        return False
    except Exception as e:
        print(f"FAIL - Loi ket noi: {type(e).__name__}: {str(e)[:160]}")
        return False

    if send_probe:
        to = to_email or user
        msg = MIMEMultipart("alternative")
        msg["From"] = env.get("MAIL_DEFAULT_SENDER") or user
        msg["To"] = to
        msg["Subject"] = "[StudentApp] Kiem tra gui email thanh cong"
        msg.attach(MIMEText("Ban da nhan duoc email kiem tra tu he thong.", "plain", "utf-8"))
        msg.attach(MIMEText(
            "<p>Xin chao,</p><p>Ban da nhan duoc email kiem tra tu he thong "
            "Quan ly Hoc sinh.</p>", "html", "utf-8"))
        try:
            with smtplib.SMTP(server, port, timeout=20) as s:
                if use_tls:
                    s.starttls()
                s.login(user, pwd)
                s.sendmail(msg["From"], [to], msg.as_string())
            print(f"OK  - Da gui email kiem tra toi {to}")
        except Exception as e:
            print(f"FAIL - Gui email loi: {type(e).__name__}: {str(e)[:160]}")
            return False

    return True

if __name__ == "__main__":
    send = "--send" in sys.argv
    to = None
    for a in sys.argv[1:]:
        if not a.startswith("-"):
            to = a
    sys.exit(0 if check(to, send) else 1)
