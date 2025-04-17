import sys
from PyQt5.QtWidgets import QApplication
from Backend.Action import FontConverterApp 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FontConverterApp()
    window.show()
    sys.exit(app.exec_())