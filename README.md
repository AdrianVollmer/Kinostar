# Kinoheld Movie Showtimes Viewer

A terminal-based movie showtime viewer for Kinoheld using the Textual
library.

## Features

- Displays current movie showtimes fetched from Kinoheld API
- Clean, scrollable interface organized chronologically by date
- Shows movie titles, durations, and all available showtimes
- Detailed movie information (description, cast, director, genres,
  ratings)
- Displays special flags (e.g., OMdU for original with subtitles)
- Configurable theaters and filters
- Keyboard shortcuts for easy navigation
- Focus navigation between movies
- Modal detail view for each movie

## Installation

This project uses `uv` for dependency management. The dependencies will
be automatically installed when you run the application.

## Usage

Run the application:

``` bash
uv run kinoheld
```

### Keyboard Shortcuts

- `q` - Quit the application
- `s` - Toggle sort (by showtimes or release date)
- `Tab` / `Shift+Tab` - Navigate between movies
- `Enter` or Click - View movie details
- `Escape` - Close detail modal
- Arrow keys / Page Up/Page Down - Scroll through showtimes

## How It Works

The application:

1.  Fetches showtime data from the Kinoheld API
2.  Organizes shows by date
3.  Groups showtimes by movie
4.  Displays everything in a clean, scrollable interface

## Data Source

Showtimes are fetched from:

- **API**: <https://www.kinoheld.de/ajax/getShowsForCinemas>
