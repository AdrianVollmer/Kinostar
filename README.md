# Kinoheld Movie Showtimes Viewer

A terminal-based movie showtime viewer for Kinoheld using the Textual
library.

## Features

- Displays current movie showtimes fetched from Kinoheld API
- Multiple theater support: configure and view showtimes for multiple
  theaters simultaneously
- **Theater search**: search for theaters by city name to find cinema IDs
- Flexible grouping: toggle between grouping by theater or by movie
- Clean, scrollable interface organized by theater/movie and date
- Shows movie titles, durations, and all available showtimes
- Detailed movie information (description, cast, director, genres,
  ratings)
- Displays special flags (e.g., OMdU for original with subtitles)
- Configurable theaters and filters (global and per-theater)
- Keyboard shortcuts for easy navigation
- Focus navigation between movies
- Modal detail view for each movie

## Installation

This project uses `uv` for dependency management. The dependencies will
be automatically installed when you run the application.

``` bash
uv tool install .
```

## Usage

Run the application:

``` bash
uv run kinoheld
```

### Keyboard Shortcuts

- `q` - Quit the application
- `s` - Toggle sort (by showtimes or release date)
- `g` - Toggle grouping (by theater or by movie)
- `f` - Search for theaters by city
- `Tab` / `Shift+Tab` - Navigate between movies
- `Enter` or Click - View movie details
- `Escape` - Close detail modal
- Arrow keys / Page Up/Page Down - Scroll through showtimes

## Theater Search

Press `f` to search for theaters by city name. This opens a search modal
where you can enter a city name (e.g., "Tübingen", "Berlin"). The app
will query the Kinoheld database and display matching theaters with
their cinema IDs, addresses, and other details.

To add a found theater to your configuration:

1.  Note the **Cinema ID** from the search results
2.  Edit your config file at `~/.config/kinostar/config.toml`
3.  Add a new `[[theaters]]` section with the cinema ID and a name

## Configuration

The app uses a configuration file located at
`~/.config/kinostar/config.toml` (or
`$XDG_CONFIG_HOME/kinostar/config.toml`).

On first run, a default configuration file will be created
automatically. You can edit this file to add multiple theaters.

### Example Configuration

``` toml
# Global filter: regex pattern to exclude movies by title (applied to all theaters)
# global_filter = "(?i)(sneak|preview)"

# Theater configurations
[[theaters]]
name = "Kino Museum"
cinema_id = 3625
default = true
# Optional: filter specific to this theater
# filter = "(?i)opera"

# Add more theaters
[[theaters]]
name = "Arsenal Kino"
cinema_id = 1234
# filter = "(?i)some_pattern"
```

### Configuration Options

- **`global_filter`**: (Optional) Regex pattern to exclude movies from
  all theaters
- **`theaters`**: Array of theater configurations
  - **`name`**: Display name for the theater
  - **`cinema_id`**: Kinoheld cinema ID (find this in the Kinoheld URL)
  - **`default`**: (Optional) Mark as default theater (currently unused,
    all theaters are displayed)
  - **`filter`**: (Optional) Regex pattern to exclude movies from this
    specific theater

## How It Works

The application:

1.  Fetches showtime data from the Kinoheld API for all configured
    theaters
2.  Organizes shows by theater and date
3.  Groups showtimes by movie
4.  Displays everything in a clean, scrollable interface with flexible
    grouping:
    - **Group by Theater** (default): Shows theater sections, with movies
      listed under each theater
    - **Group by Movie**: Shows movies grouped together, with each
      theater's showtimes displayed separately as "Movie Name [Theater
      Name]"

## Data Source

Showtimes are fetched from:

- **API**: <https://www.kinoheld.de/ajax/getShowsForCinemas>
