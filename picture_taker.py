from picamzero import Camera
from time import sleep


if __name__ == '__main__':
    path_to_save = r"../mushroom-pics/current.jpg"
    cam = Camera()
    cam.take_photo(path_to_save)