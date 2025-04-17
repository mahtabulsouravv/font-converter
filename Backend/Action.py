import sys
import os
import brotli
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon  # Add this import
from fontTools.ttLib import TTFont
from Generated.Dashboard import Ui_MainWindow

class ConversionThread(QThread):
    progress_updated = pyqtSignal(int)
    conversion_complete = pyqtSignal(bool, str)
    file_progress = pyqtSignal(str)

    def __init__(self, input_files, output_formats, output_dir, parent=None):
        super().__init__(parent)
        self.input_files = input_files
        self.output_formats = output_formats
        self.output_dir = output_dir
        self.running = True

    def run(self):
        total_files = len(self.input_files)
        success_count = 0
        
        for i, input_file in enumerate(self.input_files):
            if not self.running:
                break
                
            self.file_progress.emit(f"Processing {os.path.basename(input_file)}")
            
            try:
                font = TTFont(input_file)
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                
                for fmt in self.output_formats:
                    if not self.running:
                        break
                        
                    output_file = os.path.join(self.output_dir, f"{base_name}.{fmt}")
                    
                    try:
                        if fmt == 'woff':
                            font.flavor = 'woff'
                        elif fmt == 'woff2':
                            try:
                                font.flavor = 'woff2'
                            except Exception as e:
                                self.file_progress.emit(f"WOFF2 conversion failed (need brotli): {str(e)}")
                                continue
                        else:
                            font.flavor = None
                        
                        font.save(output_file)
                        self.file_progress.emit(f"Created {os.path.basename(output_file)}")
                        
                    except Exception as e:
                        error_msg = f"Error converting to {fmt}: {str(e)}"
                        self.file_progress.emit(error_msg)
                        continue
                
                success_count += 1
            except Exception as e:
                error_msg = f"Error processing {os.path.basename(input_file)}: {str(e)}"
                self.file_progress.emit(error_msg)
            
            progress = int((i + 1) / total_files * 100)
            self.progress_updated.emit(progress)
        
        self.conversion_complete.emit(self.running, f"Converted {success_count}/{total_files} files")

class FontConverterApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # Load the UI design
        
        # Initialize variables
        self.conversion_thread = None
        self.output_dir = None
        self.input_files = []
        
        # Reset progress bar to 0
        self.progressBar.setValue(0)
        
        # Connect signals
        self.choose_button.clicked.connect(self.select_font_files)
        self.output_button.clicked.connect(self.select_output_dir)
        self.start_button.clicked.connect(self.start_conversion)
        self.cancel_button.clicked.connect(self.cancel_conversion)
        self.cancel_button.setEnabled(False)

    def select_font_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Font files (*.ttf *.otf *.woff *.woff2 *.eot)")
        
        if file_dialog.exec_():
            self.input_files = file_dialog.selectedFiles()
            if self.input_files:
                self.label_2.setText(f"Selected {len(self.input_files)} font files")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.label_2.setText(f"Output directory: {dir_path}")

    def start_conversion(self):
        output_formats = []
        if self.eot_check.isChecked(): output_formats.append('eot')
        if self.otf_check.isChecked(): output_formats.append('otf')
        if self.ttf_check.isChecked(): output_formats.append('ttf')
        if self.woff_check.isChecked(): output_formats.append('woff')
        if self.woff2_check.isChecked(): 
            try:
                import brotli
                output_formats.append('woff2')
            except ImportError:
                QMessageBox.warning(self, "WOFF2 Error", 
                                  "WOFF2 conversion requires brotli package\nInstall with: pip install brotli")
                return
            
        if not output_formats:
            QMessageBox.warning(self, "Warning", "Please select at least one output format")
            return
            
        if not self.input_files:
            QMessageBox.warning(self, "Warning", "No files to convert")
            return
            
        output_dir = self.output_dir if self.output_dir else os.path.join(
            os.path.dirname(self.input_files[0]), 
            "converted_fonts"
        )
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        self.label_2.setText(f"Output directory: {output_dir}")
        
        self.conversion_thread = ConversionThread(self.input_files, output_formats, output_dir)
        self.conversion_thread.progress_updated.connect(self.progressBar.setValue)
        self.conversion_thread.conversion_complete.connect(self.conversion_finished)
        self.conversion_thread.file_progress.connect(self.label_2.setText)
        
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.label_2.setText("Conversion started...")
        
        self.conversion_thread.start()
        
    def conversion_finished(self, completed, message):
        # Create styled message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Completed" if completed else "Warning")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information if completed else QMessageBox.Warning)
        
        # Set window icon
        msg_box.setWindowIcon(QIcon(":/Images/logo.png"))
        msg_box.setFixedSize(500, 200)
        
        # Apply styling to match Dashboard.py
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: rgb(49, 49, 49);
                color: #ffffff;
                font-family: "Segoe UI", sans-serif;
                font-size: 16px;
            }
            QMessageBox QLabel {
                color: #ffffff;
            }
            QMessageBox QPushButton {
                font-size: 16px;
                font-family: "Segoe UI", sans-serif;
                color: #f0f0f0;
                padding: 8px 16px;
                background-color: #2f2f2f;
                border: 2px solid #444444;
                border-radius: 8px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #d88c84;
                color: #ffffff;
                border-color: #a3605a;
            }
            QMessageBox QPushButton:pressed {
                background-color: #a3605a;
                border-color: #7f4a44;
                color: #ffffff;
            }
        """)
        
        # Add OK button with custom text
        ok_button = msg_box.addButton("OK", QMessageBox.AcceptRole)
        ok_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-family: "Segoe UI", sans-serif;
                color: #f0f0f0;
                padding: 8px 16px;
                background-color: #2f2f2f;
                border: 2px solid #444444;
                border-radius: 8px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #d88c84;
                color: #ffffff;
                border-color: #a3605a;
            }
            QPushButton:pressed {
                background-color: #a3605a;
                border-color: #7f4a44;
                color: #ffffff;
            }
        """)
        
        msg_box.exec_()
        
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.label_2.setText(message)
        
    def cancel_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.running = False
            self.conversion_thread.wait()
            self.label_2.setText("Conversion cancelled")
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            
    def closeEvent(self, event):
        if self.conversion_thread and self.conversion_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Conversion in Progress',
                "A conversion is in progress. Are you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
            if reply == QMessageBox.Yes:
                self.conversion_thread.running = False
                self.conversion_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    converter = FontConverterApp()
    converter.show()
    sys.exit(app.exec_())