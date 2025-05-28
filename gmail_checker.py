import imaplib
import email

def check_gmail_for_code(gmail_user, gmail_pass, code):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_pass)
        mail.select("inbox")
        typ, data = mail.search(None, '(FROM "info@account.netflix.com")')
        email_ids = data[0].split()

        for e_id in reversed(email_ids[-10:]):
            typ, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == 'text/plain':
                                body += part.get_payload(decode=True).decode()
                    else:
                        body = msg.get_payload(decode=True).decode()

                    if code in body:
                        return True
        return False
    except Exception as e:
        print("IMAP error:", e)
        return False