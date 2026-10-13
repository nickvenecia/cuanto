"""Your Cuánto account: the sign-in window, and who's signed in. See services/account.py."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QWidget

from cuanto.services import account
from cuanto.ui.components.widgets import Embeddable, Section, button_row, hint, vbox
from cuanto.ui.style import theme, tokens


class SignInDialog(Embeddable, QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Sign In")
        self.setMinimumWidth(tokens.DIALOG_W)
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_3)
        self.word = QLabel(theme.wordmark())
        self.word.setObjectName("Wordmark")
        self.word.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.word)
        self.title_label = QLabel("Sign In to Your Account")
        self.title_label.setObjectName("DialogTitle")
        lay.addWidget(self.title_label)
        if not account.service().connected:
            lay.addWidget(hint("Accounts are coming soon. Everything works without one."))

        sec = Section("Email")
        self.email = QLineEdit()
        self.email.setPlaceholderText("you@example.com")
        sec.add(self.email)
        lay.addWidget(sec)
        sec = Section("Password")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        sec.add(self.password)
        lay.addWidget(sec)
        self.forgot = QPushButton("Forgot your password?")
        self.forgot.setObjectName("LinkBtn")
        self.forgot.clicked.connect(self._forgot)
        lay.addWidget(self.forgot)
        self.error = hint("")
        self.error.setObjectName("Bad")
        self.error.hide()
        lay.addWidget(self.error)

        row = button_row()
        self.cancel_btn = later = QPushButton("Not Now")
        later.clicked.connect(self.reject)
        self.go = QPushButton("Sign In")
        self.go.setObjectName("Primary")
        self.go.setDefault(True)
        self.go.clicked.connect(self._sign_in)
        row.addWidget(later)
        row.addWidget(self.go)
        lay.addLayout(row)

    def _say(self, text: str) -> None:
        self.error.setText(text)
        self.error.setVisible(bool(text))

    def _sign_in(self) -> None:
        try:
            account.sign_in(self.email.text(), self.password.text())
        except OSError as e:
            self._say(str(e))
            return
        finally:
            self.password.clear()  # never kept, even in this window
        self.accept()

    def _forgot(self) -> None:
        if not account.valid_email(self.email.text()):
            self._say("Type your email first.")
            return
        try:
            account.service().reset_password(self.email.text().strip())
        except OSError as e:
            self._say(str(e))
            return
        self._say("Check your email for a link to set a new password.")
