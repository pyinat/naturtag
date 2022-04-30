# https://github.com/marcel-goldschen-ohm/PyQtImageViewer
import os
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QFileDialog, QGraphicsScene, QGraphicsView, QMainWindow
from qt_material import apply_stylesheet

PWD = Path(__file__).parent.absolute()


class QtImageViewer(QGraphicsView):
    file_changed = Signal(str)

    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self._pixmapHandle = None

        self.aspectRatioMode = Qt.KeepAspectRatio
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scale_factor = 1
        self.resize_lock = False
        self.files = []
        self.img_dir = None
        self.img_name = None

        self.SUPPORTED_FILE_TYPES = [".png", ".jpg"]

    def clear_image(self):
        if self.has_image():
            self.scene.removeItem(self._pixmapHandle)
            self._pixmapHandle = None

    # return the image currently being displayed as a pixmap
    def pixmap(self):
        if self.has_image():
            return self._pixmapHandle.pixmap()
        return None

    # return the image currently being displayed as QImage
    def image(self):
        if self.has_image():
            return self._pixmapHandle.pixmap().toImage()
        return None

    # load an image from a filepath
    def file_from_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open image file:")
        self.load_file(file_name)

    def load_file(self, file_path):
        if not os.path.isfile(file_path):
            return
        self.img_dir = os.path.dirname(file_path)
        self.img_name = os.path.basename(file_path)
        self.files = [
            f for f in os.listdir(self.img_dir) if os.path.splitext(f)[-1] in self.SUPPORTED_FILE_TYPES
        ]

        # set image to be displayed on the image viewer
        image = QPixmap(file_path)
        if self._pixmapHandle:
            self._pixmapHandle.setPixmap(image)
        else:
            self._pixmapHandle = self.scene.addPixmap(image)

        # adjust the view of the scene to the pixmap
        self.setSceneRect(QRectF(image.rect()))
        self.fitInView(self.sceneRect(), self.aspectRatioMode)
        self.file_changed.emit(self.img_name)

    # def reset_viewer(self, zoom=False):
    #     if zoom:
    #         self.fitInView(self.sceneRect(), self.aspectRatioMode)
    #     self.scale_factor = 1

    # def adjust_zoom(self):
    #     self.fitInView(self.zoom_rect, self.aspectRatioMode)

    # def step(self, direction):
    #     index = self.files.index(self.img_name)

    #     if direction == "left":
    #         if index == 0:
    #             return
    #         new_img_name = os.path.join(self.img_dir, self.files[index - 1])

    #     elif direction == "right":
    #         if index + 1 == len(self.files):
    #             return
    #         new_img_name = os.path.join(self.img_dir, self.files[index + 1])

    #     self.load_file(new_img_name)

    # # Events
    # def resizeEvent(self, event):
    #     if self.resize_lock:
    #         self.resize_lock = not self.resize_lock
    #         return

    #     self.reset_viewer(zoom=True)

    # def wheelEvent(self, event):
    #     self.setTransformationAnchor(
    #         QGraphicsView.AnchorUnderMouse
    #     )  # AnchorUnderMouse # AnchorViewCenter

    #     scale_factor = 1.05
    #     if event.angleDelta().y() > 0:
    #         self.scale(scale_factor, scale_factor)
    #         self.scale_factor *= scale_factor
    #     else:
    #         self.scale(1.0 / scale_factor, 1.0 / scale_factor)
    #         self.scale_factor *= 1.0 / scale_factor

    #     self.zoom_rect = self.mapToScene(self.viewport().rect())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.count = 0

        # custom widgets
        self.ui = QUiLoader().load(PWD / "main_ui.ui", None)
        self.ui.imageViewer = QtImageViewer()
        self.ui.imageViewer.setStyleSheet("border-width: 0px; border-style: solid")
        self.ui.verticalLayout_2.addWidget(self.ui.imageViewer)

        # connect the widgets to their respective functions
        self.ui.imageViewer.file_changed.connect(lambda new_name: self.image_changed(new_name))
        self.ui.left_btn.clicked.connect(lambda: self.ui.imageViewer.step("left"))
        self.ui.right_btn.clicked.connect(lambda: self.ui.imageViewer.step("right"))
        self.ui.open_btn.clicked.connect(lambda: self.show_image())

        # window options
        self.setWindowTitle("Image Viewer")
        self.setCentralWidget(self.ui)

    def show_image(self):
        self.ui.imageViewer.file_from_file_dialog()

    def render_image(self):
        self.ui.imageViewer.render_image()

    def image_changed(self, new_name):
        self.setWindowTitle(f"Viewing \"{new_name}\"")


def run():
    app = QApplication(sys.argv)
    window = MainWindow()

    apply_stylesheet(app, theme='dark_teal.xml')
    window.showMaximized()
    app.exec()


if __name__ == '__main__':
    run()
