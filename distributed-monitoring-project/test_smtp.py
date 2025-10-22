import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sender = "juanlusianis20n@gmail.com"
receiver = "juanlopezcastrods@gmail.com"
password = "rcxx mkto ahdg ctxf"

message = MIMEMultipart()
message["From"] = sender
message["To"] = receiver
message["Subject"] = "Test SMTP"

body = "Esta es una prueba de conexión SMTP"
message.attach(MIMEText(body, "plain"))

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    text = message.as_string()
    server.sendmail(sender, receiver, text)
    print("Correo enviado exitosamente!")
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    try:
        server.quit()
    except:
        pass