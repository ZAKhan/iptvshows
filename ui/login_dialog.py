from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt
import core.database as db
from api.xtream import XtreamAPI


class LoginDialog(QDialog):
    def __init__(self, parent=None, server: dict = None):
        super().__init__(parent)
        self.server = server  # None = add new, dict = edit existing
        self.api = None
        self.server_id = None

        self.setWindowTitle("Add Server" if server is None else "Edit Server")
        self.setFixedSize(480, 360)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #121216; border: 1px solid #232329; border-radius: 14px; }
            QLabel { color: #f1efe9; }
            QLineEdit { background: #18181d; border: 1px solid #232329; border-radius: 10px;
                padding: 9px 14px; color: #f1efe9; font-size: 13px; }
            QLineEdit:focus { border-color: #ffb547; }
            QLineEdit::placeholder { color: #6b6960; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        title = QLabel("Add Server" if server is None else "Edit Server")
        title.setStyleSheet(
            'font-family: "Instrument Serif", Georgia, serif; '
            'font-size: 26px; color: #f1efe9; font-weight: 400;'
        )
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name = QLineEdit()
        self._name.setPlaceholderText("My IPTV Server")
        form.addRow("Name:", self._name)

        self._url = QLineEdit()
        self._url.setPlaceholderText("http://server.example.com:8080")
        form.addRow("Server URL:", self._url)

        self._user = QLineEdit()
        self._user.setPlaceholderText("username")
        form.addRow("Username:", self._user)

        self._pass = QLineEdit()
        self._pass.setPlaceholderText("password")
        self._pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self._pass)

        layout.addLayout(form)

        btns = QHBoxLayout()
        self._btn_test = QPushButton("Test Connection")
        self._btn_save = QPushButton("Save & Connect")
        self._btn_save.setObjectName("PlayBtn")
        self._btn_cancel = QPushButton("Cancel")
        btns.addWidget(self._btn_cancel)
        btns.addStretch()
        btns.addWidget(self._btn_test)
        btns.addWidget(self._btn_save)
        layout.addLayout(btns)

        self._btn_cancel.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06); border: 1px solid #2e2e36;
                color: #a8a59c; border-radius: 10px; padding: 10px 18px; font-size: 13px; }
            QPushButton:hover { border-color: #ff6b6b; color: #ff6b6b; }
        """)
        self._btn_test.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06); border: 1px solid #2e2e36;
                color: #a8a59c; border-radius: 10px; padding: 10px 18px; font-size: 13px; }
            QPushButton:hover { border-color: #ffb547; color: #ffb547; }
        """)
        self._btn_save.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);
                color: #1a1004; border: none; border-radius: 10px;
                padding: 10px 22px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #ffc060; }
        """)
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_test.clicked.connect(self._test)
        self._btn_save.clicked.connect(self._save)

        if server:
            self._name.setText(server.get('name', ''))
            self._url.setText(server.get('url', ''))
            self._user.setText(server.get('username', ''))
            self._pass.setText(server.get('password', ''))
            self.server_id = server.get('id')

    def _test(self):
        if not self._validate():
            return
        self._btn_test.setText("Testing…")
        self._btn_test.setEnabled(False)
        try:
            api = XtreamAPI(self._url.text().strip(), self._user.text().strip(), self._pass.text())
            api.authenticate()
            exp = api.user_info.get('exp_date', 'N/A')
            QMessageBox.information(
                self, "Success",
                f"Connected successfully!\n"
                f"Expires: {exp}\n"
                f"Status: {api.user_info.get('status', 'N/A')}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", str(e))
        finally:
            self._btn_test.setText("Test Connection")
            self._btn_test.setEnabled(True)

    def _save(self):
        if not self._validate():
            return
        name = self._name.text().strip()
        url = self._url.text().strip()
        user = self._user.text().strip()
        pw = self._pass.text()

        if self.server_id:
            db.update_server(self.server_id, name, url, user, pw)
            self.server_id = self.server_id
        else:
            self.server_id = db.add_server(name, url, user, pw)

        db.set_active_server(self.server_id)
        self.accept()

    def _validate(self) -> bool:
        if not self._url.text().strip():
            QMessageBox.warning(self, "Missing Field", "Please enter a server URL.")
            return False
        if not self._user.text().strip():
            QMessageBox.warning(self, "Missing Field", "Please enter a username.")
            return False
        if not self._pass.text():
            QMessageBox.warning(self, "Missing Field", "Please enter a password.")
            return False
        return True
