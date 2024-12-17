
def create_bottom_frame(root, screen_width, screen_height):
    """Create the bottom frame with a status and animated corner graphic."""
    global server_status_label

    bottom_frame = tk.Frame(root, bg="white", height=calculate_height(0.2, screen_height), bd=0)
    bottom_frame.pack(side="bottom", fill="x")

    # Load and animate the corner GIF
    gif_path = get_image_path("swirl.gif")
    if gif_path and os.path.exists(gif_path):  # Ensure the file exists
        gif_frames = []  # Store the GIF frames

        # Load GIF frames
        gif_img = Image.open(gif_path)
        for frame_index in range(gif_img.n_frames):
            gif_img.seek(frame_index)  # Go to the current frame
            current_frame = gif_img.copy().convert("RGBA")  # Copy and convert frame to RGBA
            gif_frames.append(ImageTk.PhotoImage(current_frame))  # Convert to Tk-compatible image

        # Create a label to display the GIF
        gif_label = tk.Label(bottom_frame, bg="white", bd=0)  # Use `bottom_frame` here
        gif_label.pack(side="right", padx=0, pady=0)

        # Function to animate the GIF
        def animate_gif(index):
            gif_label.config(image=gif_frames[index])  # Update the label's image
            next_index = (index + 1) % len(gif_frames)  # Loop back to the first frame
            gif_label.after(100, animate_gif, next_index)  # Adjust delay for smooth animation

        # Start the animation
        animate_gif(0)

        # Keep references to prevent garbage collection
        root.gif_frames = gif_frames
        root.gif_label = gif_label
    else:
        print("Error: GIF file not found or path is invalid:", gif_path)

    return bottom_frame  # Return the renamed frame