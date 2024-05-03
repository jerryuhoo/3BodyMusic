import pygame
from random import *
import numpy as np
import time
import sys
import math

from pythonosc import udp_client

osc_client = udp_client.SimpleUDPClient("127.0.0.1", 5555)

# initiate pygame and clock
pygame.init()
clock = pygame.time.Clock()
game_font = pygame.font.SysFont("ubuntu", 15)

# dimensions
WIDTH = 1200
HEIGHT = 600

# gravitational constant
g = 0.5
# g = 4.4

# set up colors:
BLACK = (0, 0, 0)
BLUE = (0, 191, 255)
YELLOW = (255, 240, 100)
GREEN = (10, 128, 0)
RED = (250, 10, 10)
WHITE = (255, 255, 255)

# set up surface plane
surface = pygame.display.set_mode((WIDTH, HEIGHT))  # ((width, height))
pygame.display.set_caption("3 body")

# Load background image
background_image = pygame.image.load("background.jpeg")
background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))

# set up trails
global trails_active
trails_active = True

border_radius = 10
# trails button
trails_button = pygame.Rect(10, 10, 80, 30)
trails_button_surface = game_font.render("TRAILS", True, (0, 0, 0))
pygame.draw.rect(surface, WHITE, trails_button, border_radius=border_radius)
surface.blit(trails_button_surface, (50, 10))

# reset button
reset_button = pygame.Rect(110, 10, 80, 30)
reset_button_surface = game_font.render("RESET", True, (0, 0, 0))
pygame.draw.rect(surface, WHITE, reset_button, border_radius=border_radius)
surface.blit(reset_button_surface, (WIDTH / 2 - 30, 10))

# exit button
exit_button = pygame.Rect(210, 10, 80, 30)
exit_button_surface = game_font.render("EXIT", True, (0, 0, 0))
pygame.draw.rect(surface, WHITE, exit_button, border_radius=border_radius)
surface.blit(exit_button_surface, (WIDTH - 90, 10))


class Slider:
    def __init__(
        self,
        x,
        y,
        w,
        h,
        min_val,
        max_val,
        initial_val,
        color=(200, 200, 200),
        hover_color=(150, 150, 150),
    ):
        self.rect = pygame.Rect(x, y, w, h)  # Slider rectangle
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val  # Current value
        self.active = False  # If the slider is being dragged
        self.color = color
        self.hover_color = hover_color
        self.handle_rect = pygame.Rect(
            x + (w * ((initial_val - min_val) / (max_val - min_val))) - 10,
            y - 5,
            20,
            h + 10,
        )

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_rect.collidepoint(event.pos):
                self.active = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.active = False
        elif event.type == pygame.MOUSEMOTION and self.active:
            self.handle_rect.x = min(
                max(event.pos[0] - 10, self.rect.x), self.rect.x + self.rect.width - 20
            )
            self.val = self.min_val + (
                (self.handle_rect.x + 10 - self.rect.x) / self.rect.width
            ) * (self.max_val - self.min_val)

    def draw(self, screen):
        pygame.draw.rect(
            screen, self.hover_color if self.active else self.color, self.rect
        )
        pygame.draw.rect(screen, (255, 255, 255), self.handle_rect)
        val_surface = game_font.render(f"gravity:{self.val:.2f}", True, (255, 255, 255))
        # draw text
        screen.blit(val_surface, (self.rect.x + self.rect.width + 5, self.rect.y))


g_slider = Slider(320, 15, 200, 20, 0, 5, 0.5)


def draw_circle(surface, color, position, size):
    # Ensure that the circle has a minimum size of 1
    if size < 1:
        size = 1
    pygame.draw.circle(surface, color, position, int(size))


############################## celestial body object
class Body(object):
    def __init__(self, m, x, y, r, c):
        """
        mass = m,
        position = [x, y],
        color = c,
        radius = r
        """
        # mass, postion (x, y), color
        self.mass = m
        self.position = np.array([x, y])
        self.last_position = np.array([x, y])
        self.velocity = np.array([0, 0])
        self.accel = np.array([randint(-1, 1), randint(-1, 1)])
        self.color = c
        self.radius = r
        self.trail = []  # List to store recent trail segments
        self.bounce = 0
        self.last_bounce = 0

    def applyForce(self, force):
        # apply forces to a body
        f = force / self.mass
        self.accel = np.add(self.accel, f)

    def update(self):
        # update position based on velocity and reset accel
        if self.bounce > 12:
            self.bounce = 0
        self.velocity = np.add(self.velocity, self.accel)
        self.last_position = self.position
        self.position = np.add(self.position, self.velocity)
        self.accel = 0
        if (
            self.position[0] - self.radius <= 0
            or self.position[0] + self.radius >= WIDTH
        ):
            self.velocity[0] = -self.velocity[0]  # Reverse horizontal velocity
            self.bounce += 1
        if (
            self.position[1] - self.radius <= 0
            or self.position[1] + self.radius >= HEIGHT
        ):
            self.velocity[1] = -self.velocity[1]
            self.bounce += 1

        # Append current position to the trail
        self.trail.append(self.position.copy())

        ### Change Tail Length HERE !!! ###
        if len(self.trail) > 255:
            self.trail.pop(0)  # Remove the oldest segment
        osc_client.send_message("/body_position", [self.position[0], self.position[1]])

    def display(self):
        # draw over old object location
        pygame.draw.circle(
            surface,
            BLACK,
            (int(self.last_position[0]), int(self.last_position[1])),
            self.radius,
        )  # (drawLayer, color, (coordinates), radius)

        # draw trail OLD (Comment this line out to remove trails)
        # if trails_active == True:
        #     start_pos = (int(self.last_position[0]), int(self.last_position[1]))
        #     end_pos = (int(self.position[0]), int(self.position[1]))
        #     print(f"{start_pos}, {end_pos}")
        #     pygame.draw.line(
        #         surface,
        #         WHITE,
        #         (int(self.last_position[0]), int(self.last_position[1])),
        #         (int(self.position[0]), int(self.position[1])),
        #         5,
        #     )

        # # draw trail NEW
        # if trails_active == True:
        #     for i in range(len(self.trail) - 1):
        #         start_pos = (int(self.trail[i][0]), int(self.trail[i][1]))
        #         end_pos = (int(self.trail[i + 1][0]), int(self.trail[i + 1][1]))
        #         alpha = int(len(self.trail) - i - 1)
        #         if alpha > 255:
        #             alpha = 255
        #         color = (self.color[0], alpha, self.color[2], alpha)
        #         pygame.draw.line(
        #             surface, color, start_pos, end_pos, 1
        #         )  # (255, 255, 255, alpha)

        if trails_active:
            # Total number of circles in the trail
            num_circles = len(self.trail)

            # Determine the maximum size of the circles
            max_circle_size = 10  # You can adjust this value

            # The starting size of the largest circle and fade effect
            for i in range(num_circles):
                pos = (int(self.trail[i][0]), int(self.trail[i][1]))

                # Gradual decrease in alpha and size
                # The circle at the start of the trail is smallest and most transparent
                alpha = int(255 * (i + 1) / num_circles) * 0.8
                if alpha > 255:
                    alpha = 255
                elif alpha < 0:
                    alpha = 0  # Ensure alpha stays within the valid range

                # Adjust circle size based on its position in the trail
                circle_size = max_circle_size * (i + 1) / num_circles

                # Create color with changing alpha
                # Gradually change the color component as well
                color = (
                    int(self.color[0] * alpha / 255),
                    int(self.color[1] * alpha / 255),
                    int(self.color[2] * alpha / 255),
                    alpha,
                )

                # Draw circle
                pygame.draw.circle(surface, color, pos, int(circle_size))

        # Draw glow effect
        pygame.draw.circle(
            surface,
            (
                min(255, int(self.color[0] + 100)),
                min(255, int(self.color[1] + 100)),
                min(255, int(self.color[2] + 100)),
                255,
            ),
            (int(self.position[0]), int(self.position[1])),
            self.radius * 1.3,  # Larger radius for the glow
        )

        # draw new object location
        pygame.draw.circle(
            surface,
            self.color,
            (int(self.position[0]), int(self.position[1])),
            self.radius,
        )

    def attract(self, m, g):
        # gravitational code rewritten from Daniel Shiffman's "Nature of Code"
        force = self.position - m.position
        distance = np.linalg.norm(force)
        distance = constrain(distance, 5.0, 25.0)
        force = normalize(force)
        strength = (g * self.mass * m.mass) / float(distance * distance)
        force = force * strength
        return force

    def randomize_position(self):
        self.position[0] = randrange(WIDTH)
        self.position[1] = randrange(HEIGHT)
        self.velocity = np.array([0, 0])
        return


############################## set up and draw
def setup():
    side_length = min(WIDTH, HEIGHT) // 2
    triangle_height = side_length * 3**0.5 / 2
    center_x = WIDTH / 2
    center_y = HEIGHT / 2 - triangle_height / 2

    # planets
    body1 = Body(10, center_x, center_y, 10, RED)  # randint(0, 10)
    body2 = Body(1, center_x - side_length / 2, center_y + triangle_height, 6, GREEN)
    body3 = Body(2.62, center_x + side_length / 2, center_y + triangle_height, 8, BLUE)

    # list of all bodies
    global bodies
    bodies = [body1, body2, body3]
    # bodies = [body1, body2]
    return


def draw():

    surface.blit(background_image, (0, 0))

    for index, body in enumerate(bodies):
        for other_body in bodies:
            if body != other_body:
                force = other_body.attract(body, g)
                body.applyForce(force)
        body.update()
        body.display()

        osc_client.send_message(
            f"/body_position{index + 1}", [body.position[0], body.position[1]]
        )
        overall_velocity = math.sqrt(body.velocity[0] ** 2 + body.velocity[1] ** 2)
        osc_client.send_message(
            f"/body_velocity{index + 1}",
            overall_velocity,
        )
        if body.bounce != body.last_bounce:
            osc_client.send_message(
                f"/body_bounce{index + 1}",
                body.bounce,
            )
            body.last_bounce = body.bounce

    for body in bodies:
        body.display()

    pygame.draw.rect(surface, WHITE, trails_button, border_radius=border_radius)
    surface.blit(trails_button_surface, (20, 15))

    pygame.draw.rect(surface, WHITE, reset_button, border_radius=border_radius)
    surface.blit(reset_button_surface, (120, 15))

    pygame.draw.rect(surface, WHITE, exit_button, border_radius=border_radius)
    surface.blit(exit_button_surface, (230, 15))

    return


############################## mathematical functions


def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))


def normalize(force):
    normal = np.linalg.norm(force, ord=1)
    try:
        if normal == 0:
            normal = np.finfo(force.dtype).eps
        return force / normal
    except:
        return force


# main loop
if __name__ == "__main__":
    # initial set up
    setup()
    while True:
        # draw bodies to screen
        draw()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Update the slider based on input
            g_slider.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                # trails button
                if trails_button.collidepoint(mouse_pos):
                    print("trails button pushed")
                    if trails_active == True:
                        trails_active = False
                        surface.fill(BLACK)
                    else:
                        trails_active = True
                if exit_button.collidepoint(mouse_pos):
                    pygame.quit()
                    sys.exit()
                if reset_button.collidepoint(mouse_pos):
                    for body in bodies:
                        body.randomize_position()
                    surface.fill(BLACK)

        # Draw the slider
        g_slider.draw(surface)
        # Update gravitational constant g
        g = g_slider.val

        if pygame.mouse.get_pressed()[0]:
            mouse_pos = pygame.mouse.get_pos()
            mouse_posx = mouse_pos[0]
            mouse_posy = mouse_pos[1]

            # move bodies
            radius_factor = 5
            for body in bodies:
                if (
                    body.position[0] - body.radius * radius_factor
                    <= mouse_pos[0]
                    <= body.position[0] + body.radius * radius_factor
                ):
                    if (
                        body.position[1] - body.radius * radius_factor
                        <= mouse_pos[1]
                        <= body.position[1] + body.radius * radius_factor
                    ):
                        # safe check
                        if mouse_posx < 10:
                            mouse_posx = 10
                        if mouse_posx > WIDTH - 10:
                            mouse_posx = WIDTH - 10
                        if mouse_posy < 10:
                            mouse_posy = 10
                        if mouse_posy > HEIGHT - 10:
                            mouse_posy = HEIGHT - 10

                        body.position = np.array([mouse_posx, mouse_posy])
                        body.velocity = np.array([0, 0])
                        body.trail = []
                        body.bounce = 0
                        body.last_bounce = 0

        pygame.display.update()
        time.sleep(0.001)
