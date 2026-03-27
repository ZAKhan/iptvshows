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
        self.setFixedSize(440, 320)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("Add Server" if server is None else "Edit Server")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #c4bbfc; letter-spacing: -0.3px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
