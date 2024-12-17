import tkinter as tk
from PIL import Image, ImageTk
import rlottie

def create_gui_with_lottie():
    """
    Creates the GUI and displays a Lottie animation in the bottom-right corner.
    """
    # Root window configuration
    root = tk.Tk()
    root.title("Noatime Stempeluhr")
    root.attributes('-zoomed', True)
    root.config(bg="white")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Top Frame (for date and other content)
    top_frame = tk.Frame(root, bg="white")
    top_frame.pack(side="top", fill="x")

    # Clock Label
    global clock_label
    clock_label = tk.Label(top_frame, text="", bg="white", fg="black", font=("Arial", 24))
    clock_label.pack(pady=(10, 5))

    # Center Frame (for other content)
    center_frame = tk.Frame(root, bg="white")
    center_frame.pack(expand=True, fill="both")

    # Bottom Frame (for Lottie animation)
    bottom_frame = tk.Frame(root, bg="white")
    bottom_frame.pack(side="bottom", fill="x")

    # Lottie Canvas in Bottom Frame
    lottie_canvas_width = int(screen_width * 0.3)
    lottie_canvas_height = int(screen_height * 0.3)
    lottie_canvas = tk.Canvas(bottom_frame, bg="white", width=lottie_canvas_width, height=lottie_canvas_height)
    lottie_canvas.pack(side="right", anchor="se", padx=10, pady=10)

    # Load the Lottie animation
    lottie_path = "/home/admin_noatime/noatime/animations/caw.json"  # Replace with your Lottie JSON file path
    animation = rlottie.Animation.from_file(lottie_path)

    # Frame parameters
    frame_index = 0
    total_frames = animation.total_frames()
    duration = 1000 / animation.frame_rate()  # Frame duration in milliseconds

    def update_lottie():
        """
        Updates the canvas with the next frame of the Lottie animation.
        """
        nonlocal frame_index

        # Render the current frame
        surface = animation.render(frame_index, lottie_canvas_width, lottie_canvas_height)

        # Convert the frame to a PIL Image
        frame_image = Image.frombuffer("RGBA", (lottie_canvas_width, lottie_canvas_height), surface, "raw", "RGBA", 0, 1)

        # Convert the PIL Image to an ImageTk object
        tk_image = ImageTk.PhotoImage(frame_image)

        # Display the frame on the canvas
        lottie_canvas.create_image(lottie_canvas_width // 2, lottie_canvas_height // 2, image=tk_image)
        lottie_canvas.image = tk_image  # Prevent garbage collection

        # Update to the next frame
        frame_index = (frame_index + 1) % total_frames
        root.after(int(duration), update_lottie)

    # Start the Lottie animation
    update_lottie()

    # Start the main loop
    root.mainloop()

# Run the GUI
create_gui_with_lottie()
