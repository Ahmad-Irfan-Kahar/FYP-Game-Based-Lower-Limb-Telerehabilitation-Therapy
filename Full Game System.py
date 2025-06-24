import pygame
import sys
import os
import random
import csv
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import requests
from button import Button
import serial
import time
from time import sleep
from datetime import datetime

pygame.init()

# Global Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
GAME_SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
user = None

# Serial Communication constants
port = "COM8"
baud_rate = 115200

# Firebase setup
cred = credentials.Certificate(r"your-private-key")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'lower-limb-telerehabilitation'})
API_KEY = "your-api-key-here"

# Initialize Firestore
db = firestore.client()

# Constant for Marching while sitting Game
PLAYER_WIDTH = 100
PLAYER_HEIGHT = 100
HURDLE_WIDTH = 100
HURDLE_HEIGHT = 80
GAME_BG_COLOR = (255, 255, 255)

RUNNING = [pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Running man.png")), (PLAYER_WIDTH, PLAYER_HEIGHT))]
JUMPING = [pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Running man.png")), (PLAYER_WIDTH, PLAYER_HEIGHT))]
HURDLE = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Hurdle.png")), (HURDLE_WIDTH, HURDLE_HEIGHT))
MarchingBG = pygame.image.load(os.path.join("Assets", "Ground.png"))

# Constant for Ankleflexion Game
BIRD_WIDTH = 60
BIRD_HEIGHT = 60
COIN_WIDTH = 80
COIN_HEIGHT = 80
last_obstacle_height = 100
height_index = 0  # Start at the first height in the sequence

BIRD = [pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Bird.png")), (BIRD_WIDTH, BIRD_HEIGHT))]
MOVING = [pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Bird.png")), (BIRD_WIDTH, BIRD_HEIGHT))]
COINS = pygame.transform.scale(pygame.image.load(os.path.join("Assets", "Coin.png")), (COIN_WIDTH, COIN_HEIGHT))
BG = pygame.image.load(os.path.join("Assets", "AnkleGround.png"))
BG = pygame.transform.scale(BG, (SCREEN_WIDTH, 100))

# Constants for Login System
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Login System")
BG_LOGIN = pygame.image.load("assets/Lobby.png")

# Font helper function
def get_font(size):
    return pygame.font.Font("assets/font.ttf", size)

# Input box class
class InputBox:
    def __init__(self, x, y, w, h, font, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = pygame.Color('white')
        self.text = text
        self.font = font
        self.txt_surface = font.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            self.txt_surface = self.font.render(self.text, True, self.color)

    def draw(self, screen):
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        pygame.draw.rect(screen, self.color, self.rect, 2)

# Runner class for Marching Game
class Runner:
    X_POS = 50
    Y_POS = 350
    GRAVITY = 7

    def __init__(self):
        self.run_img = RUNNING
        self.jump_img = JUMPING

        self.player_run = True
        self.player_jump = False

        self.jump_vel = self.GRAVITY
        self.image = self.run_img[0]
        self.player_rect = self.image.get_rect()
        self.player_rect.x = self.X_POS
        self.player_rect.y = self.Y_POS
    
    def update2(self, input2):
        if self.player_run:
            self.run()

        if self.player_jump:
            self.jump()

        if input2 == 'JUMP' and not self.player_jump:
            self.player_run = False
            self.player_jump = True

        elif not self.player_jump:
            self.player_run = True
            self.player_jump = False

    def run(self):
        self.image = self.run_img[0]
        self.player_rect = self.image.get_rect()
        self.player_rect.x = self.X_POS
        self.player_rect.y = self.Y_POS

    def jump(self):
        self.image = self.jump_img[0]
        if self.player_jump:
            self.player_rect.y -= self.jump_vel * 4
            self.jump_vel -= 0.5

        if self.jump_vel < -self.GRAVITY:
            self.player_jump = False
            self.jump_vel = self.GRAVITY

    def update(self, userInput):

        if self.player_run:
            self.run()

        if self.player_jump:
            self.jump()

        if userInput[pygame.K_UP] and not self.player_jump:
            self.player_run = False
            self.player_jump = True

        elif not self.player_jump:
            self.player_run = True
            self.player_jump = False

    def run(self):
        self.image = self.run_img[0]
        self.player_rect = self.image.get_rect()
        self.player_rect.x = self.X_POS
        self.player_rect.y = self.Y_POS

    def jump(self):
        self.image = self.jump_img[0]
        if self.player_jump:
            self.player_rect.y -= self.jump_vel * 4
            self.jump_vel -= 0.5

        if self.jump_vel < -self.GRAVITY:
            self.player_jump = False
            self.jump_vel = self.GRAVITY

    def draw(self, SCREEN):
        SCREEN.blit(self.image, (self.player_rect.x, self.player_rect.y))

# Obstacle class for Marching Game
class Obstacle:
    def __init__(self):
        self.image = HURDLE
        self.rect = self.image.get_rect()
        self.rect.x = SCREEN_WIDTH
        self.rect.y = 380
        self.collided = False  # Track collision with the player

    def update(self):
        self.rect.x -= game_speed
        if self.rect.x < -self.rect.width:  # Remove obstacle if it moves off-screen
            obstacles.pop()

    def draw(self, SCREEN):
        SCREEN.blit(self.image, (self.rect.x, self.rect.y))

# Marching Game (EASY) main Loop
def MarchingGameE():
    global game_speed, x_pos_bg, y_pos_bg, points, obstacles

    run = True
    game_over = False
    data_saved = False
    clock = pygame.time.Clock()
    player = Runner()
    game_speed = 12
    x_pos_bg = 0
    y_pos_bg = 340
    points = 0
    start_time = pygame.time.get_ticks()
    font = get_font(30)
    obstacles = []
    accelZ_data = []

    # Initialize Serial Connection
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        print(f"Connected to {port} at {baud_rate} baud.")
        time.sleep(2)  # Wait for ESP32 to reset
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        ser = None

    def score():
        text = font.render("Score: " + str(points), True, (0, 0, 0))
        SCREEN.blit(text, (1000, 50))

    def timer():
        # Calculate the time remaining
        elapsed_time = (pygame.time.get_ticks() - start_time) // 1000
        remaining_time = max(0, 30 - elapsed_time)
        minutes = remaining_time // 60
        seconds = remaining_time % 60
        time_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, (0, 0, 0))
        SCREEN.blit(time_text, (470, 10))
        return remaining_time

    def background():
        global x_pos_bg, y_pos_bg
        image_width = MarchingBG.get_width()
        SCREEN.blit(MarchingBG, (x_pos_bg, y_pos_bg))
        SCREEN.blit(MarchingBG, (image_width + x_pos_bg, y_pos_bg))

        if x_pos_bg <= -image_width:
            x_pos_bg = 0

        x_pos_bg -= game_speed

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if game_over and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if back_button_rect.collidepoint(mouse_pos):
                    return  # Return to the main menu

        SCREEN.fill((255, 255, 255))
        userInput = pygame.key.get_pressed()

        if not game_over:
            # Read data from Serial (if connected)
            if ser.in_waiting > 0:
                # Read a line from the serial port
                line = ser.readline().decode('utf-8').strip()
                ax, ay, az, gx, gy, gz = map(int, line.split(','))
                
                # Calculate acceleration Z in g's
                accelZ = az / 16384.0
                accelZ_data.append(accelZ)
                
                # Process data and control the game
                if accelZ > -0.6:
                    print("JUMP")
                    player.update2('JUMP')
                
            remaining_time = timer()
            if remaining_time <= 0:
                game_over = True

            # Player actions
            player.draw(SCREEN)
            player.update(userInput)

            # Obstacle actions
            if len(obstacles) == 0:
                obstacles.append(Obstacle())

            for obstacle in obstacles:
                obstacle.draw(SCREEN)
                obstacle.update()

                # Collision logic
                if player.player_rect.colliderect(obstacle.rect):
                    obstacle.collided = True

                # Scoring logic
                if obstacle.rect.x + obstacle.rect.width < player.player_rect.x and not obstacle.collided:
                    points += 1
                    obstacles.pop()  # Remove the obstacle after scoring

            # Update background and score
            background()
            score()

        else:
            # Game Over logic
            game_over_text = get_font(50).render("Game Over", True, (0, 0, 0))
            game_over_rect = game_over_text.get_rect(center=(640, SCREEN_HEIGHT // 2 - 50))
            SCREEN.blit(game_over_text, game_over_rect)

            final_score_text = get_font(20).render(f"Final Score: {points}", True, (0, 0, 0))
            final_score_rect = final_score_text.get_rect(center=(640, SCREEN_HEIGHT // 2 + 10))
            SCREEN.blit(final_score_text, final_score_rect)

            back_button_text = get_font(20).render("Back to Menu", True, (0, 0, 0))
            back_button_rect = back_button_text.get_rect(bottomright=(1250, 600))
            SCREEN.blit(back_button_text, back_button_rect)
            
            if not data_saved:
                save_to_firestore("Marching_Level1", points)
                filename = construct_filename(username, "Marching", "level1")
                save_accelZ_to_csv(accelZ_data, filename)
                upload_to_firebase(filename)
                
                data_saved = True

        clock.tick(30)
        pygame.display.update()
    
    # Close Serial Connection
    if ser:
        ser.close()
        print("Serial connection closed.")

# Marching Game (HARD) main Loop
def MarchingGameH():
    global game_speed, x_pos_bg, y_pos_bg, points, obstacles

    run = True
    game_over = False
    data_saved = False
    clock = pygame.time.Clock()
    player = Runner()
    game_speed = 24
    x_pos_bg = 0
    y_pos_bg = 340
    points = 0
    start_time = pygame.time.get_ticks()
    font = get_font(30)
    obstacles = []
    accelZ_data = []

    # Initialize Serial Connection
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        print(f"Connected to {port} at {baud_rate} baud.")
        time.sleep(2)  # Wait for ESP32 to reset
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        ser = None

    def score():
        text = font.render("Score: " + str(points), True, (0, 0, 0))
        SCREEN.blit(text, (1000, 50))

    def timer():
        # Calculate the time remaining
        elapsed_time = (pygame.time.get_ticks() - start_time) // 1000
        remaining_time = max(0, 30 - elapsed_time)
        minutes = remaining_time // 60
        seconds = remaining_time % 60
        time_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, (0, 0, 0))
        SCREEN.blit(time_text, (470, 10))
        return remaining_time

    def background():
        global x_pos_bg, y_pos_bg
        image_width = MarchingBG.get_width()
        SCREEN.blit(MarchingBG, (x_pos_bg, y_pos_bg))
        SCREEN.blit(MarchingBG, (image_width + x_pos_bg, y_pos_bg))

        if x_pos_bg <= -image_width:
            x_pos_bg = 0

        x_pos_bg -= game_speed

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if game_over and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if back_button_rect.collidepoint(mouse_pos):
                    return  # Return to the main menu

        SCREEN.fill((255, 255, 255))
        userInput = pygame.key.get_pressed()

        if not game_over:
            # Read data from Serial (if connected)
            if ser.in_waiting > 0:
                # Read a line from the serial port
                line = ser.readline().decode('utf-8').strip()
                ax, ay, az, gx, gy, gz = map(int, line.split(','))
                
                # Calculate acceleration Z in g's
                accelZ = az / 16384.0
                accelZ_data.append(accelZ)
                
                # Process data and control the game
                if accelZ > -0.6:
                    print("JUMP")
                    player.update2('JUMP')

            remaining_time = timer()
            if remaining_time <= 0:
                game_over = True

            # Player actions
            player.draw(SCREEN)
            player.update(userInput)

            # Obstacle actions
            if len(obstacles) == 0:
                obstacles.append(Obstacle())

            for obstacle in obstacles:
                obstacle.draw(SCREEN)
                obstacle.update()

                # Collision logic
                if player.player_rect.colliderect(obstacle.rect):
                    obstacle.collided = True

                # Scoring logic
                if obstacle.rect.x + obstacle.rect.width < player.player_rect.x and not obstacle.collided:
                    points += 1
                    obstacles.pop()  # Remove the obstacle after scoring

            # Update background and score
            background()
            score()

        else:
            # Game Over logic
            game_over_text = get_font(50).render("Game Over", True, (0, 0, 0))
            game_over_rect = game_over_text.get_rect(center=(640, SCREEN_HEIGHT // 2 - 50))
            SCREEN.blit(game_over_text, game_over_rect)

            final_score_text = get_font(20).render(f"Final Score: {points}", True, (0, 0, 0))
            final_score_rect = final_score_text.get_rect(center=(640, SCREEN_HEIGHT // 2 + 10))
            SCREEN.blit(final_score_text, final_score_rect)

            back_button_text = get_font(20).render("Back to Menu", True, (0, 0, 0))
            back_button_rect = back_button_text.get_rect(bottomright=(1250, 600))
            SCREEN.blit(back_button_text, back_button_rect)

            if not data_saved:
                save_to_firestore("Marching_Level2", points)
                filename = construct_filename(username, "Marching", "level1")
                save_accelZ_to_csv(accelZ_data, filename)
                upload_to_firebase(filename)
                
                data_saved = True

        clock.tick(30)
        pygame.display.update()

    # Close Serial Connection
    if ser:
        ser.close()
        print("Serial connection closed.")

# Coins class for Ankle Game (EASY & MEDIUM)
class coins:
    def __init__(self):
        self.image = COINS
        self.rect = self.image.get_rect()
        self.rect.x = SCREEN_WIDTH
        # Initialize the height based on the global counter
        global last_obstacle_height
        self.rect.y = 150 if last_obstacle_height == 450 else 450
        last_obstacle_height = self.rect.y

    def update(self):
        self.rect.x -= game_speed
        if self.rect.x < -self.rect.width:  # When it goes off screen
            obstacles.pop()  # Remove this obstacle from the list

    def draw(self, SCREEN):
        SCREEN.blit(self.image, (self.rect.x, self.rect.y))

# Flying class for Ankle Game (EASY & MEDIUM)
class Flying:
    X_POS = 50
    Y_POS_UP = 150  # Height when the player moves up
    Y_POS_DOWN = 450  # Height when the player moves down
    MOVE_SPEED = 15  # Speed of transition between positions

    def __init__(self):
        self.image = BIRD[0]
        self.target_y_pos = self.Y_POS_DOWN  # Initial target position is DOWN
        self.current_y_pos = self.Y_POS_DOWN  # Start at DOWN position
        self.player_rect = self.image.get_rect()
        self.player_rect.x = self.X_POS
        self.player_rect.y = self.current_y_pos

    def update(self, userInput):
        # Check for key presses to change target position
        if userInput[pygame.K_UP]:
            self.target_y_pos = self.Y_POS_UP

        if userInput[pygame.K_DOWN]:
            self.target_y_pos = self.Y_POS_DOWN

        # Smoothly move towards the target position
        if self.current_y_pos < self.target_y_pos:  # Move down
            self.current_y_pos += self.MOVE_SPEED
            if self.current_y_pos > self.target_y_pos:  # Ensure no overshooting
                self.current_y_pos = self.target_y_pos

        if self.current_y_pos > self.target_y_pos:  # Move up
            self.current_y_pos -= self.MOVE_SPEED
            if self.current_y_pos < self.target_y_pos:  # Ensure no overshooting
                self.current_y_pos = self.target_y_pos

        # Update the player's rectangle position
        self.player_rect.y = self.current_y_pos

    def update2(self, input2):
        # Check for key presses to change target position
        if input2 == 'UP':
            self.target_y_pos = self.Y_POS_UP

        if input2 == 'DOWN':
            self.target_y_pos = self.Y_POS_DOWN

        # Smoothly move towards the target position
        if self.current_y_pos < self.target_y_pos:  # Move down
            self.current_y_pos += self.MOVE_SPEED
            if self.current_y_pos > self.target_y_pos:  # Ensure no overshooting
                self.current_y_pos = self.target_y_pos

        if self.current_y_pos > self.target_y_pos:  # Move up
            self.current_y_pos -= self.MOVE_SPEED
            if self.current_y_pos < self.target_y_pos:  # Ensure no overshooting
                self.current_y_pos = self.target_y_pos

        # Update the player's rectangle position
        self.player_rect.y = self.current_y_pos

    def draw(self, SCREEN):
        SCREEN.blit(self.image, (self.player_rect.x, self.player_rect.y))

# Ankle Game (EASY) main loop
def AnkleGameE():
    global game_speed, x_pos_bg, y_pos_bg, points, obstacles

    run = True
    game_over = False  
    data_saved = False
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()  # Record the start time
    player = Flying()
    game_speed = 20
    x_pos_bg = 0
    y_pos_bg = 340
    points = 0
    font = get_font(30)
    obstacles = []
    pitch_data = []

    # Initialize Serial Connection
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        print(f"Connected to {port} at {baud_rate} baud.")
        time.sleep(2)  # Wait for ESP32 to reset
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        ser = None

    def score():
        text = font.render("Score: " + str(points), True, (0, 0, 0))
        SCREEN.blit(text, (1000, 50))

    def timer():
        # Calculate the time remaining
        elapsed_time = (pygame.time.get_ticks() - start_time) // 1000
        remaining_time = max(0, 30 - elapsed_time)
        minutes = remaining_time // 60
        seconds = remaining_time % 60
        time_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, (0, 0, 0))
        SCREEN.blit(time_text, (470, 10))
        return remaining_time

    def background():
        global x_pos_bg, y_pos_bg
        image_width = BG.get_width()
        SCREEN.blit(BG, (x_pos_bg, y_pos_bg + 300))
        SCREEN.blit(BG, (image_width + x_pos_bg, y_pos_bg + 300))

        if x_pos_bg <= -image_width:
            x_pos_bg = 0

        x_pos_bg -= game_speed

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Check for "Back to Menu" button press when the game is over
            if game_over and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if back_button_rect.collidepoint(mouse_pos):
                    return  # Return to the main menu

        SCREEN.fill((0, 204, 255))
        userInput = pygame.key.get_pressed()

        if not game_over:
            if ser.in_waiting > 0:
                # Read a line from the serial port
                line = ser.readline().decode('utf-8').strip()
                ax, ay, az, gx, gy, gz = map(int, line.split(','))
                
                # Calculate pitch in degrees/sec
                pitch = gy / 131.0
                pitch_data.append(pitch)
                
                # Process data and control the game
                if pitch < -30.0:
                    print("UP")
                    player.update2('UP')
                elif pitch > 30.0:
                    print("DOWN")
                    player.update2('DOWN')

            player.draw(SCREEN)
            player.update(userInput)

            # coins actions
            if len(obstacles) == 0:
                obstacles.append(coins())

            for obstacle in obstacles:
                obstacle.draw(SCREEN)
                obstacle.update()

                # Check for "collecting" (collision with obstacle)
                if player.player_rect.colliderect(obstacle.rect):
                    points += 1
                    obstacles = [o for o in obstacles if o != obstacle]

            # Update background, score, and timer
            background()
            score()
            remaining_time = timer()

            # End the game if the time is up
            if remaining_time == 0:
                game_over = True
        
        else:
            # Draw "Game Over" text
            game_over_text = get_font(50).render("Game Over", True, (0 ,0 ,0))
            game_over_rect = game_over_text.get_rect(center=(640, SCREEN_HEIGHT // 2 - 50))
            pygame.draw.rect(SCREEN, (0, 204, 255), game_over_rect.inflate(20, 20))  # Draw background for game over text
            SCREEN.blit(game_over_text, game_over_rect)

            # Draw final score text
            final_score_text = get_font(20).render(f"Final Score: {points}", True, (0 ,0 ,0))
            final_score_rect = final_score_text.get_rect(center=(640, SCREEN_HEIGHT // 2 + 10))
            pygame.draw.rect(SCREEN, (0, 204, 255), final_score_rect.inflate(20, 20))  # Draw background for score
            SCREEN.blit(final_score_text, final_score_rect)

            # Draw "Back to Menu" button at the bottom right
            back_button_text = get_font(20).render("Back to Menu", True, (0 ,0 ,0))
            back_button_rect = back_button_text.get_rect(bottomright=(1250, 600))
            pygame.draw.rect(SCREEN, (0, 204, 255), back_button_rect.inflate(20, 20))  # Draw background for button
            SCREEN.blit(back_button_text, back_button_rect)

            # Background scrolling
            image_width = BG.get_width()
            SCREEN.blit(BG, (x_pos_bg, y_pos_bg + 300))
            SCREEN.blit(BG, (image_width + x_pos_bg, y_pos_bg + 300))

            if not data_saved:
                save_to_firestore("Ankle_Level1", points)
                filename = construct_filename(username, "Ankle", "level1")
                save_accelZ_to_csv(pitch_data, filename)
                upload_to_firebase(filename)
                
                data_saved = True

        clock.tick(30)
        pygame.display.update()

    # Close Serial Connection
    if ser:
        ser.close()
        print("Serial connection closed.")

# Ankle Game (HARD) main loop
def AnkleGameH():
    global game_speed, x_pos_bg, y_pos_bg, points, obstacles

    run = True
    game_over = False
    data_saved = False
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()  # Record the start time
    player = Flying()
    game_speed = 40
    x_pos_bg = 0
    y_pos_bg = 340
    points = 0
    font = get_font(30)
    obstacles = []
    pitch_data = []

    # Initialize Serial Connection
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        print(f"Connected to {port} at {baud_rate} baud.")
        time.sleep(2)  # Wait for ESP32 to reset
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        ser = None

    def score():
        text = font.render("Score: " + str(points), True, (0, 0, 0))
        SCREEN.blit(text, (1000, 50))

    def timer():
        # Calculate the time remaining
        elapsed_time = (pygame.time.get_ticks() - start_time) // 1000
        remaining_time = max(0, 30 - elapsed_time)
        minutes = remaining_time // 60
        seconds = remaining_time % 60
        time_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, (0, 0, 0))
        SCREEN.blit(time_text, (470, 10))
        return remaining_time

    def background():
        global x_pos_bg, y_pos_bg
        image_width = BG.get_width()
        SCREEN.blit(BG, (x_pos_bg, y_pos_bg + 300))
        SCREEN.blit(BG, (image_width + x_pos_bg, y_pos_bg + 300))

        if x_pos_bg <= -image_width:
            x_pos_bg = 0

        x_pos_bg -= game_speed

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Check for "Back to Menu" button press when the game is over
            if game_over and event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if back_button_rect.collidepoint(mouse_pos):
                    return  # Return to the main menu

        SCREEN.fill((0, 204, 255))
        userInput = pygame.key.get_pressed()

        if not game_over:
            if ser.in_waiting > 0:
                # Read a line from the serial port
                line = ser.readline().decode('utf-8').strip()
                ax, ay, az, gx, gy, gz = map(int, line.split(','))
                
                # Calculate acceleration Z in g's and pitch in degrees/sec
                pitch = gy / 131.0
                pitch_data.append(pitch)
                
                # Process data and control the game
                if pitch < -30.0:
                    print("UP")
                    player.update2('UP')
                elif pitch > 30.0:
                    print("DOWN")
                    player.update2('DOWN')

            player.draw(SCREEN)
            player.update(userInput)

            # coins actions
            if len(obstacles) == 0:
                obstacles.append(coins())

            for obstacle in obstacles:
                obstacle.draw(SCREEN)
                obstacle.update()

                # Check for "collecting" (collision with obstacle)
                if player.player_rect.colliderect(obstacle.rect):
                    points += 1
                    obstacles = [o for o in obstacles if o != obstacle]

            # Update background, score, and timer
            background()
            score()
            remaining_time = timer()

            # End the game if the time is up
            if remaining_time == 0:
                game_over = True
        
        else:
            # Draw "Game Over" text
            game_over_text = get_font(50).render("Game Over", True, (0 ,0 ,0))
            game_over_rect = game_over_text.get_rect(center=(640, SCREEN_HEIGHT // 2 - 50))
            pygame.draw.rect(SCREEN, (0, 204, 255), game_over_rect.inflate(20, 20))  # Draw background for game over text
            SCREEN.blit(game_over_text, game_over_rect)

            # Draw final score text
            final_score_text = get_font(20).render(f"Final Score: {points}", True, (0 ,0 ,0))
            final_score_rect = final_score_text.get_rect(center=(640, SCREEN_HEIGHT // 2 + 10))
            pygame.draw.rect(SCREEN, (0, 204, 255), final_score_rect.inflate(20, 20))  # Draw background for score
            SCREEN.blit(final_score_text, final_score_rect)

            # Draw "Back to Menu" button at the bottom right
            back_button_text = get_font(20).render("Back to Menu", True, (0 ,0 ,0))
            back_button_rect = back_button_text.get_rect(bottomright=(1250, 600))
            pygame.draw.rect(SCREEN, (0, 204, 255), back_button_rect.inflate(20, 20))  # Draw background for button
            SCREEN.blit(back_button_text, back_button_rect)

            # Background scrolling
            image_width = BG.get_width()
            SCREEN.blit(BG, (x_pos_bg, y_pos_bg + 300))
            SCREEN.blit(BG, (image_width + x_pos_bg, y_pos_bg + 300))

            if not data_saved:
                save_to_firestore("Ankle_Level2", points)
                filename = construct_filename(username, "Ankle", "level2")
                save_accelZ_to_csv(pitch_data, filename)
                upload_to_firebase(filename)
                
                data_saved = True

        clock.tick(30)
        pygame.display.update()

    # Close Serial Connection
    if ser:
        ser.close()
        print("Serial connection closed.")
    
# Login system page
def login_page():
    global user, username

    LOGIN_TEXT = get_font(75).render("PATIENT LOGIN", True, "#b68f40")
    LOGIN_RECT = LOGIN_TEXT.get_rect(center=(640, 100))

    email_input = InputBox(450, 300, 500, 40, get_font(25))
    password_input = InputBox(450, 400, 500, 40, get_font(25))
    login_button = pygame.Rect(500, 500, 120, 50)
    register_button = pygame.Rect(660, 500, 180, 50)

    while True:
        SCREEN.blit(BG_LOGIN, (0, 0))
        mouse_pos = pygame.mouse.get_pos()

        email_input.draw(SCREEN)
        password_input.draw(SCREEN)

        pygame.draw.rect(SCREEN, (0, 0, 0), login_button)
        pygame.draw.rect(SCREEN, (0, 0, 0), register_button)

        login_text = get_font(20).render("Login", True, "White")
        register_text = get_font(20).render("Register", True, "White")
        SCREEN.blit(login_text, (login_button.x + 10, login_button.y + 15))
        SCREEN.blit(register_text, (register_button.x + 10, register_button.y + 15))

        email_label = get_font(20).render("Email:", True, "White")
        password_label = get_font(20).render("Password:", True, "White")
        SCREEN.blit(LOGIN_TEXT, LOGIN_RECT)
        SCREEN.blit(email_label, (330, 310))
        SCREEN.blit(password_label, (270, 410))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            email_input.handle_event(event)
            password_input.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if login_button.collidepoint(mouse_pos):
                    if email_input.text and password_input.text:
                        try:
                            # Authenticate user (fetch user by email)
                            user = auth.get_user_by_email(email_input.text)

                            # Retrieve user data from Firestore
                            user_doc = db.collection("Patients").document(user.uid).get()
                            if user_doc.exists:
                                user_data = user_doc.to_dict()
                                print(f"Welcome back, {user_data['name']}!")
                                print(f"User Email: {user_data['email']}")
                                username = user_data['name']
                                main_menu()
                            else:
                                print("User record not found in Firestore!")

                        except Exception as e:
                            print(f"Login failed: {e}")
                    else:
                        print("Please enter your email and password!")

                if register_button.collidepoint(mouse_pos):
                    register_page()

        pygame.display.update()

# Registration system page
def register_page():
    email_input = InputBox(450, 300, 500, 40, get_font(25))
    password_input = InputBox(450, 400, 500, 40, get_font(25))
    name_input = InputBox(450, 200, 500, 40, get_font(25))
    register_button = pygame.Rect(500, 500, 320, 50)

    REGISTER_TEXT = get_font(50).render("ACCOUNT REGISTRATION", True, "#b68f40")
    REGISTER_RECT = REGISTER_TEXT.get_rect(center=(640, 100))

    while True:
        SCREEN.blit(BG_LOGIN, (0, 0))
        mouse_pos = pygame.mouse.get_pos()

        email_input.draw(SCREEN)
        password_input.draw(SCREEN)
        name_input.draw(SCREEN)
        pygame.draw.rect(SCREEN, (0, 0, 0), register_button)

        register_text = get_font(20).render("Create Account", True, "White")
        SCREEN.blit(register_text, (register_button.x + 20, register_button.y + 15))

        email_label = get_font(20).render("Email:", True, "White")
        password_label = get_font(20).render("Password:", True, "White")
        name_label = get_font(20).render("Name:", True, "White")
        SCREEN.blit(email_label, (330, 310))
        SCREEN.blit(password_label, (270, 410))
        SCREEN.blit(name_label, (350, 210))
        SCREEN.blit(REGISTER_TEXT, REGISTER_RECT)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            email_input.handle_event(event)
            password_input.handle_event(event)
            name_input.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if register_button.collidepoint(mouse_pos):
                    if email_input.text and password_input.text and name_input.text:
                        try:
                            # Create the user in Firebase Authentication
                            user = auth.create_user(
                                email=email_input.text,
                                password=password_input.text,
                                display_name=name_input.text
                            )

                            # Save user details in Firestore
                            db.collection("Patients").document(user.uid).set({
                                "name": name_input.text,
                                "email": email_input.text,
                                "created_at": firestore.SERVER_TIMESTAMP
                            })

                            print(f"Account created successfully for {user.display_name}!")
                            login_page()
                        except Exception as e:
                            print(f"Registration failed: {e}")
                    else:
                        print("Please fill in all fields!")

        pygame.display.update()

def main_menu():
    while True:
        SCREEN.blit(BG_LOGIN, (0, 0))
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        MENU_TEXT = get_font(100).render("MAIN MENU", True, "#b68f40")
        MENU_RECT = MENU_TEXT.get_rect(center=(640, 100))

        PLAY_BUTTON = Button(image=pygame.image.load("assets/Play Rect.png"), pos=(640, 350), 
                             text_input="PLAY", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        
        QUIT_BUTTON = Button(image=pygame.image.load("assets/Play Rect.png"), pos=(640, 550), 
                             text_input="QUIT", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        
        SCREEN.blit(MENU_TEXT, MENU_RECT)

        PLAY_BUTTON.changeColor(MENU_MOUSE_POS)
        PLAY_BUTTON.update(SCREEN)

        QUIT_BUTTON.changeColor(MENU_MOUSE_POS)
        QUIT_BUTTON.update(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if PLAY_BUTTON.checkForInput(MENU_MOUSE_POS):
                    game_selection()
                
                if QUIT_BUTTON.checkForInput(MENU_MOUSE_POS):
                    pygame.quit()
                    sys.exit()
        
        pygame.display.update()

#Game selection page
def game_selection():
    while True:
        SCREEN.blit(BG_LOGIN, (0, 0))  # Background image
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        # Display title text
        MENU_TEXT = get_font(39).render("Select the Exercise", True, "#b68f40")
        MENU_RECT = MENU_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(MENU_TEXT, MENU_RECT)

        # Define button rectangles with adjusted positions
        MARCHING_RECT = pygame.Rect(440, 240, 400, 100)  # Marching Game button
        ANKLE_RECT = pygame.Rect(440, 450, 400, 100)     # Ankleflexion Game button
        QUIT_RECT = pygame.Rect(1050, 660, 200, 50)     # Quit Button

        # Function to draw buttons with hover effect
        def draw_button(rect, text, base_color, hover_color):
            color = hover_color if rect.collidepoint(MENU_MOUSE_POS) else base_color
            pygame.draw.rect(SCREEN, color, rect)
            button_text = get_font(20).render(text, True, "Black")
            button_text_rect = button_text.get_rect(center=rect.center)
            SCREEN.blit(button_text, button_text_rect)

        # Draw buttons
        draw_button(MARCHING_RECT, "Marching Game", "#b68f40", "White")
        draw_button(ANKLE_RECT, "Ankleflexion Game", "#b68f40", "White")
        draw_button(QUIT_RECT, "Back", "#b68f40", "White")

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if MARCHING_RECT.collidepoint(MENU_MOUSE_POS):
                    marchinggame_level_selection()  # Go to marching game level selection
                elif ANKLE_RECT.collidepoint(MENU_MOUSE_POS):
                    anklegame_level_selection()  # Go to ankle flexion game level selection
                elif QUIT_RECT.collidepoint(MENU_MOUSE_POS):
                    pygame.quit()
                    sys.exit()

        pygame.display.update()

# Marching Game level selection page
def marchinggame_level_selection():
    while True:
        SCREEN.blit(BG_LOGIN, (0, 0))
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        # Display title text
        MENU_TEXT = get_font(39).render("Choose Difficulty Level", True, "#b68f40")
        MENU_RECT = MENU_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(MENU_TEXT, MENU_RECT)

        # Define button rectangles
        EASY_RECT = pygame.Rect(540, 250, 200, 50)
        HARD_RECT = pygame.Rect(540, 450, 200, 50)
        BACK_RECT = pygame.Rect(1050, 660, 200, 50)

        # Draw rectangles and text for buttons
        def draw_button(rect, text, base_color, hover_color):
            color = hover_color if rect.collidepoint(MENU_MOUSE_POS) else base_color
            pygame.draw.rect(SCREEN, color, rect)
            button_text = get_font(20).render(text, True, "Black")
            button_text_rect = button_text.get_rect(center=rect.center)
            SCREEN.blit(button_text, button_text_rect)

        draw_button(EASY_RECT, "Level 1", "#b68f40", "White")
        draw_button(HARD_RECT, "Level 2", "#b68f40", "White")
        draw_button(BACK_RECT, "Back", "#b68f40", "White")

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if EASY_RECT.collidepoint(MENU_MOUSE_POS):
                    MarchingGameE()
                elif HARD_RECT.collidepoint(MENU_MOUSE_POS):
                    MarchingGameH()
                elif BACK_RECT.collidepoint(MENU_MOUSE_POS):
                    game_selection()

        pygame.display.update()

# Ankleflexion Game level selection page
def anklegame_level_selection():
    while True:
        SCREEN.blit(BG_LOGIN, (0, 0))
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        # Display title text
        MENU_TEXT = get_font(39).render("Choose Difficulty Level", True, "#b68f40")
        MENU_RECT = MENU_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(MENU_TEXT, MENU_RECT)

        # Define button rectangles
        EASY_RECT = pygame.Rect(540, 250, 200, 50)
        HARD_RECT = pygame.Rect(540, 450, 200, 50)
        BACK_RECT = pygame.Rect(1050, 660, 200, 50)

        # Draw rectangles and text for buttons
        def draw_button(rect, text, base_color, hover_color):
            color = hover_color if rect.collidepoint(MENU_MOUSE_POS) else base_color
            pygame.draw.rect(SCREEN, color, rect)
            button_text = get_font(20).render(text, True, "Black")
            button_text_rect = button_text.get_rect(center=rect.center)
            SCREEN.blit(button_text, button_text_rect)

        draw_button(EASY_RECT, "Level 1", "#b68f40", "White")
        draw_button(HARD_RECT, "Level 2", "#b68f40", "White")
        draw_button(BACK_RECT, "Back", "#b68f40", "White")

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if EASY_RECT.collidepoint(MENU_MOUSE_POS):
                    AnkleGameE()
                elif HARD_RECT.collidepoint(MENU_MOUSE_POS):
                    AnkleGameH()
                elif BACK_RECT.collidepoint(MENU_MOUSE_POS):
                    game_selection()

        pygame.display.update()

def save_to_firestore(game_name, score):
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    subcollection_name = f"{game_name}_{date_str}"
    
    # Get a reference to the user's document
    user_doc_ref = db.collection("Patients").document(user.uid)

    # Fetch the document snapshot
    doc_snapshot = user_doc_ref.get()

    # Check if the document exists
    if doc_snapshot.exists:
        # Now access the subcollection using the user_doc_ref
        subcollection_ref = user_doc_ref.collection('Rehabilitation Sessions').document(subcollection_name)

    # Save score and raw data
    subcollection_ref.set({
        'final_score': score,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

def save_accelZ_to_csv(data, filename):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["accelZ"])  # Write header
        for value in data:
            writer.writerow([value])  # Write each value in a new row

def upload_to_firebase(filename):
    bucket = storage.bucket()  # Get the bucket
    blob = bucket.blob(filename)  # Create a blob object from the filename
    blob.upload_from_filename(filename)  # Upload the file
    print(f"{filename} uploaded to Firebase Storage.")

def construct_filename(user_name, game_type, level):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M")

    filename = f"{user_name}_{game_type}_{level}_{date_str}_{time_str}.csv"
    return filename

# Start the program
login_page()
