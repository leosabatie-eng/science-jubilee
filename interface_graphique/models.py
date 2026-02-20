from constants import *

class DraggableObject:
    def __init__(self, canvas, x, y, w, h, color, name, check_collision_callback, check_inside_callback):
        self.canvas = canvas
        self.name = name
        self.angle = 0
        self.check_collision = check_collision_callback
        self.check_inside = check_inside_callback

        self.id = canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline="white", width=2)
        self.text = canvas.create_text(x + w/2, y + h/2, text=name, fill="white", font=("Arial", 10))
        self.items = [self.id, self.text]

        for item in self.items:
            canvas.tag_bind(item, "<Button-1>", self.start_drag)
            canvas.tag_bind(item, "<B1-Motion>", self.do_drag)
            canvas.tag_bind(item, "<Button-3>", self.rotate)

    def start_drag(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def do_drag(self, event):
        dx = event.x - self.start_x
        dy = event.y - self.start_y
        x1, y1, x2, y2 = self.canvas.coords(self.id)
        w, h = x2 - x1, y2 - y1

        if self.check_inside(x1 + dx, y1 + dy, w, h) and self.check_collision(x1 + dx, y1 + dy, w, h, ignore_id=self.id):
            for item in self.items:
                self.canvas.move(item, dx, dy)
            self.start_x = event.x
            self.start_y = event.y

    def rotate(self, event):
        x1, y1, x2, y2 = self.canvas.coords(self.id)
        w, h = x2 - x1, y2 - y1
        cx, cy = x1 + w/2, y1 + h/2
        self.canvas.coords(self.id, cx - h/2, cy - w/2, cx + h/2, cy + w/2)
        self.canvas.coords(self.text, cx, cy)
        self.angle = (self.angle + 90) % 360