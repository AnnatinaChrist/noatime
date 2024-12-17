import tkinter as tk
from PIL import Image, ImageTk

root = tk.Tk()

# Path to your GIF
gif_path = "swirl.gif"

# Load GIF frames
gif_frames = []
gif_img = Image.open(gif_path)
for frame_index in range(gif_img.n_frames):
    gif_img.seek(frame_index)
    frame = gif_img.copy().convert("RGBA")
    gif_frames.append(ImageTk.PhotoImage(frame))

# Create a label to display the GIF
gif_label = tk.Label(root, bg="white")
gif_label.pack()

# Function to animate the GIF
def animate_gif(index):
    gif_label.config(image=gif_frames[index])
    next_index = (index + 1) % len(gif_frames)
    gif_label.after(100, animate_gif, next_index)

# Start the animation
animate_gif(0)

root.mainloop()
