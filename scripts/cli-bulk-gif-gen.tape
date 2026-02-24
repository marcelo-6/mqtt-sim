# (Output is provided via `vhs -o ...` from the shell script)

# Bigger output (dimensions are in pixels)
Set Width 1600
Set Height 600
Set FontSize 24

# No dramitic effect...
Set TypingSpeed 0ms

# Type a command in the terminal.
Type 'uv run mqtt-sim run -c "$config"'

# Run the command by pressing enter.
Enter

# Admire the output for a bit.
Sleep 5s

# Stop the process.
Ctrl+C