import pandas as pd
import numpy as np
from bokeh.plotting import figure, output_file, save
from bokeh.models import (
    ColumnDataSource, HoverTool, ColorBar, LinearColorMapper, CustomJS,
    TextInput, Span, Label
)
from bokeh.palettes import Viridis256
from bokeh.layouts import row, column
from bokeh.embed import components

# Path to your data files
le_df_path = r"../Important DataFrames/height_histograms_le_df.csv"
histograms_path = r"../Important DataFrames/team_height_histograms.npy"

# Load LE data
le_df = pd.read_csv(le_df_path, index_col='Roster')

# Get season from roster
le_df['Season'] = le_df.index.str[:4].astype(int)

# Load histogram data
histograms = np.load(histograms_path, allow_pickle=True).item()

# Set up height bins matching the original analysis
# Bins with edges at 73.5, 76.5, 79.5, etc.
height_min = 70.5  # Start at 70.5 inches
height_max = 91.5  # End at 91.5 inches
bin_edges = np.array([70.5, 73.5, 76.5, 79.5, 82.5, 85.5, 88.5, 91.5])
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2  # Centers of each bin

# Create data sources
scatter_source = ColumnDataSource(le_df)

# Create a dictionary of roster IDs for search functionality
roster_dict = {roster: i for i, roster in enumerate(le_df.index)}

# Initialize with first roster's histogram
first_roster = le_df.index[0]

# Now we'll aggregate the original histograms into our new bins
def aggregate_histogram(hist_data, original_min, original_max, new_edges):
    """Aggregate fine-grained histogram into specified bins"""
    original_bins = len(hist_data)
    original_edges = np.linspace(original_min, original_max, original_bins + 1)
    original_widths = original_edges[1] - original_edges[0]
    
    results = np.zeros(len(new_edges) - 1)
    
    for i, (left, right) in enumerate(zip(new_edges[:-1], new_edges[1:])):
        # Find indices in original bins that fall within this new bin
        start_idx = max(0, int((left - original_min) / original_widths))
        end_idx = min(original_bins, int((right - original_min) / original_widths))
        
        # Sum those bins
        results[i] = sum(hist_data[start_idx:end_idx])
    
    return results

# Create aggregated histograms for all teams
aggregated_histograms = {}
for roster, hist in histograms.items():
    aggregated_histograms[roster] = aggregate_histogram(
        hist, 66, 90, bin_edges)  # Using your original min/max range

# Initialize histogram data source with first roster
hist_source = ColumnDataSource(data={
    'x': bin_centers,
    'y': aggregated_histograms[first_roster],
    'roster': [first_roster] * len(bin_centers)
})

# Create scatter plot
p1 = figure(
    title='NBA Team Height Distributions (2001-2024) - Laplacian Eigenmaps',
    x_axis_label='Component 1 (Avg Height)',
    y_axis_label='Component 2 (Height Variance)',
    width=700,
    height=550,
    tools='pan,wheel_zoom,box_zoom,reset,save'
)

# Style improvements
p1.title.text_font_size = "16pt"
p1.title.align = "center"
p1.axis.axis_label_text_font_size = "14pt"
p1.axis.axis_label_text_font_style = "bold"
p1.background_fill_color = "#f8f9fa"
p1.border_fill_color = "#ffffff"
p1.outline_line_color = "#cccccc"
p1.grid.grid_line_color = "#eeeeee"

# Color mapper for seasons
mapper = LinearColorMapper(palette=Viridis256, low=le_df['Season'].min(), high=le_df['Season'].max())

# Add scatter points
scatter = p1.scatter(
    x='LE_Component_1',
    y='LE_Component_2',
    source=scatter_source,
    size=10,
    alpha=0.8,
    fill_color={'field': 'Season', 'transform': mapper},
    line_color="white",
    line_width=0.5,
    selection_color={"field": "Season", "transform": mapper},
    selection_line_color="red",
    selection_line_width=2,
    selection_alpha=1.0
)

# Create histogram plot
p2 = figure(
    title='Team Height Distribution',
    x_axis_label='Height (inches)',
    y_axis_label='Number of Players',
    width=450,
    height=550,
    y_range=(0, 10),
    x_range=(70, 92),
    tools='pan,wheel_zoom,box_zoom,reset,save'
)

# Style improvements
p2.title.text_font_size = "14pt"
p2.title.align = "center"
p2.axis.axis_label_text_font_size = "12pt"
p2.axis.axis_label_text_font_style = "bold"
p2.background_fill_color = "#f8f9fa"
p2.border_fill_color = "#ffffff"
p2.outline_line_color = "#cccccc"
p2.grid.grid_line_color = "#eeeeee"
p2.yaxis.minor_tick_line_color = None

# Set x-axis ticks to show height in feet-inches format
height_ticks = [72, 75, 78, 81, 84, 87, 90]
p2.xaxis.ticker = height_ticks
p2.xaxis.major_label_overrides = {
    h: f"{h//12}'{h%12}\"" for h in height_ticks
}

p2.yaxis.ticker = list(range(11))

# Add bin edge vertical lines for reference
for edge in bin_edges:
    line = Span(location=edge, dimension='height', line_color='gray', line_width=0.5, line_dash='dashed')
    p2.add_layout(line)
    
# Add bin labels at the bottom
for i, center in enumerate(bin_centers):
    bin_label = Label(
        x=center, y=0.2,
        text_font_size="8pt",
        text_color="gray",
        text_align="center"
    )
    p2.add_layout(bin_label)

# Add histogram bars with width matching bin size (3 inches)
hist_bars = p2.vbar(
    x='x',
    top='y',
    width=2.5,  # Slightly less than 3 to create small gaps
    source=hist_source,
    fill_color="#1d428a",
    line_color="white",
    fill_alpha=0.8
)

# Add hover tool
hover = HoverTool(renderers=[scatter])
hover.tooltips = [
    ('Team', '@Roster'),
    ('Season', '@Season'),
]

# Create a search text input
search_input = TextInput(title="Search for a team (e.g., 2016GSW):", width=300)

# Create the JavaScript callback for the search box
search_callback = CustomJS(
    args=dict(
        source=scatter_source, 
        hist_source=hist_source,
        hist_plot=p2,
        histograms=aggregated_histograms,
        roster_dict=roster_dict,
        scatter=scatter
    ),
    code="""
    // Get the search query
    const query = cb_obj.value.trim();
    
    // Reset all point selections first
    scatter.glyph.line_color = "white";
    scatter.glyph.line_width = 0.5;
    
    // Check if the query matches a roster
    if (roster_dict.hasOwnProperty(query)) {
        // Get the index of the roster in the data source
        const idx = roster_dict[query];
        
        // Get the roster
        const roster = source.data.Roster[idx];
        
        // Update the histogram title
        hist_plot.title.text = `Height Distribution for ${roster}`;
        
        // Find the histogram for this roster
        const hist_data = histograms[roster];
        
        // Update the histogram source
        hist_source.data.y = hist_data;
        hist_source.data.roster = Array(hist_data.length).fill(roster);
        
        // Highlight the selected point with a red circle
        source.selected.indices = [idx];
        
        // Trigger update
        hist_source.change.emit();
    }
    """
)

# Attach callback to the search input
search_input.js_on_change('value', search_callback)

# Create the JavaScript callback for the hover
hover_callback = CustomJS(
    args=dict(
        source=scatter_source,
        hist_source=hist_source,
        hist_plot=p2,
        histograms=aggregated_histograms,
        search_input=search_input,
        scatter=scatter
    ),
    code="""
    // Get the index of the hovered point
    const ind = cb_data.index.indices[0];
    if (ind !== undefined) {
        // Get the roster from the scatter source data
        const roster = source.data.Roster[ind];
        
        // Update the search input
        search_input.value = roster;
        
        // Update the histogram title
        hist_plot.title.text = `Height Distribution for ${roster}`;
        
        // Find the histogram for this roster
        const hist_data = histograms[roster];
        
        // Update the histogram source
        hist_source.data.y = hist_data;
        hist_source.data.roster = Array(hist_data.length).fill(roster);
        
        // Highlight the selected point
        source.selected.indices = [ind];
        
        // Trigger update
        hist_source.change.emit();
    }
    """
)

# Attach the hover callback
hover.callback = hover_callback

# Add the hover tool to the plot
p1.add_tools(hover)

# Add color bar for season
color_bar = ColorBar(
    color_mapper=mapper,
    width=10,
    location=(0, 0),
    title='Season',
    title_text_font_size="12pt",
    title_text_font_style="bold",
    title_standoff=12
)
p1.add_layout(color_bar, 'right')

# Create layout with search bar
layout = column(
    search_input,
    row(p1, p2)
)

# Output to file
output_file("nba_height_visualization_enhanced.html")
save(layout)

# Also generate components for embedding
script, div = components(layout)

# Save components to files
with open("bokeh_script_enhanced.js", "w") as f:
    f.write(script)

with open("bokeh_div_enhanced.html", "w") as f:
    f.write(div)

# Create a simple standalone embedding
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Team Height Distribution Analysis</title>
    
    <!-- Bokeh CSS and JS -->
    <link rel="stylesheet" href="https://cdn.bokeh.org/bokeh/release/bokeh-2.4.3.min.css">
    <link rel="stylesheet" href="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-2.4.3.min.css">
    <link rel="stylesheet" href="https://cdn.bokeh.org/bokeh/release/bokeh-tables-2.4.3.min.css">
    
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-2.4.3.min.js"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-2.4.3.min.js"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-2.4.3.min.js"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-api-2.4.3.min.js"></script>
    
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        
        header {{
            background-color: #1d428a;
            color: white;
            padding: 20px;
            text-align: center;
            border-bottom: 5px solid #c8102e;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        h1 {{
            margin: 0;
            font-size: 2.2em;
        }}
        
        .subtitle {{
            font-style: italic;
            margin-top: 8px;
            font-weight: 300;
        }}
        
        .instructions {{
            background-color: #fffaed;
            border-left: 4px solid #ffc107;
            padding: 12px 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>NBA Team Height Distribution Analysis (2001-2024)</h1>
        <div class="subtitle">Exploring the evolution of roster height patterns</div>
    </header>
    
    <div class="container">
        <div class="instructions">
            <strong>How to use:</strong> 
            <ul>
                <li>Hover over any team point on the left chart to see its height distribution</li>
                <li>Search for a specific team by typing its ID (e.g., 2016GSW for 2016 Golden State Warriors)</li>
                <li>Points are colored by season - newer seasons appear in lighter colors</li>
            </ul>
        </div>
        
        {div}
    </div>
    
    {script}
</body>
</html>
"""

# Save the standalone embedding
with open("nba_team_heights_interactive.html", "w") as f:
    f.write(html_content)

print("Enhanced visualization files generated successfully!")
print("1. nba_height_visualization_enhanced.html - standalone Bokeh output")
print("2. nba_team_heights_interactive.html - complete interactive webpage")
print("3. bokeh_script_enhanced.js and bokeh_div_enhanced.html - components for embedding")