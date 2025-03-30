import imaplib
import re

class OTPFetcher:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.mail.login(email, password)
        self.mail.select('inbox')

    def fetch_otp(self):
        self.mail.select('inbox')
        _, data = self.mail.search(None, 'ALL')
        latest_email_id = data[0].split()[-1]
        _, data = self.mail.fetch(latest_email_id, '(RFC822)')
        raw_email = str(data[0][1])
        
        # find 6 digit otp using regex
        otp = re.search(r'\b\d{6}\b', raw_email)
        return otp.group() if otp else None