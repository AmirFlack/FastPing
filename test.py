import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout

class CircularButtonDemo(QWidget):
    def __init__(self):
        super().__init__()

        # Create a horizontal layout
        layout = QHBoxLayout()

        # Define the small size for the buttons
        size = 30  # Adjust this value to make the buttons smaller or larger

        # Create and style three circular buttons
        for i in range(3):
            button = QPushButton(f'{i+1}', self)
            button.setFixedSize(size, size)
            button.setStyleSheet(f'''
                QPushButton {{
                    border-radius: {size // 2}px;
                    border: 1px solid #555;
                    background-color: #DDD;
                }}
                QPushButton:hover {{
                    background-color: #BBB;
                }}
                QPushButton:pressed {{
                    background-color: #999;
                }}
            ''')
            layout.addWidget(button)

        self.setLayout(layout)
        self.setWindowTitle('Small Circular Buttons Example')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    demo = CircularButtonDemo()
    demo.show()
    sys.exit(app.exec_())
