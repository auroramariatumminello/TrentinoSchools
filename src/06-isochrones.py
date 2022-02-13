# %%
# Libraries
import geopandas as gpd
import networkx as nx
import osmnx as ox
import folium
from shapely.geometry import Point

# %%
# Reading school files
schools = gpd.read_file(
    "../data/Trentino/schools/schools.geojson", geometry="geometry")

# Save list for the website, in order to choose the school
schools['Nome'].to_json("../data/schools_list_for_select.json")

index = 0
place = schools.loc[index, 'geometry']
network_type = ['walk', 'bike', 'drive_service']
trip_times = [5, 10, 15, 20]  # in minutes
colors = ['#fecc5c', '#fd8d3c', '#f03b20', '#bd0026']
colors.reverse()

# %%
def get_graph(place, net_type):
    # Get the graph with the specified network type around a place
    G = ox.graph_from_point((place.y, place.x), network_type=net_type)

    # Project the graph to EPSG7
    G = ox.project_graph(G, to_crs="EPSG:4326")
    return G

def get_center_node(G, place):
    center_node = ox.nearest_nodes(G, place.x, place.y)
    return center_node

Gs = [get_graph(place, x) for x in network_type]
# %%
# ROUTE ISOCHRONES

def get_folium_route_time_distance_map(G, place, trip_times, colors):
    # Creating the map
    map = folium.Map(location=(place.y, place.x),
                     tiles='cartodbpositron')

    # Getting the closest node point in G to the place
    center_node = get_center_node(G, place) 

    # Compute the subnetwork of streets reachable in every trip time
    # (from furthest to closest)
    for trip_time, color in zip(sorted(trip_times, reverse=True), colors):
        subgraph = nx.ego_graph(G, center_node,
                                radius=trip_time, distance='time')
        ox.plot_graph_folium(subgraph, graph_map=map,
                             color=color)

    # Adjusting map boundaries
    map.fit_bounds(map.get_bounds())

    # # Adding layers for styling
    # folium.TileLayer("cartodbpositron", name="Light").add_to(map)
    # folium.TileLayer("Cartodb dark_matter", name="Dark").add_to(map)
    # folium.TileLayer('openstreetmap', name="OpenStreetMap").add_to(map)
    # folium.LayerControl().add_to(map)
    return map

get_folium_route_time_distance_map(Gs[0],place, trip_times, colors)

# %%
# POLYGONS ISOCHRONES
def style(feature):
    print(feature)
    return {
        'fillColor': feature['properties']['color'],
        'color': feature['properties']['color'],
        'weight': 1
    }

# make the isochrone polygons
def get_folium_isochrone_map(G, place, trip_times, colors):
    isochrone_polys = []
    center_node = get_center_node(G, place)
    for trip_time in sorted(trip_times, reverse=True):
        subgraph = nx.ego_graph(
            G, center_node, radius=trip_time, distance='time')
        node_points = [Point((data['x'], data['y']))
                       for node, data in subgraph.nodes(data=True)]
        bounding_poly = gpd.GeoSeries(node_points).unary_union.convex_hull
        isochrone_polys.append(bounding_poly)

    isochrone_polys = gpd.GeoDataFrame(
        geometry=isochrone_polys, crs="EPSG:4326")
    print(isochrone_polys)
    map = folium.Map(location=(place.y, place.x),
                     zoom_start=13,
                     tiles=None)

    folium.TileLayer("cartodbpositron", name="Light").add_to(map)
    folium.TileLayer("Cartodb dark_matter", name="Dark").add_to(map)
    folium.TileLayer('openstreetmap', name="OpenStreetMap").add_to(map)
    for x in range(len(isochrone_polys)-1):
        isochrone_polys.loc[x, 'geometry'] = isochrone_polys.loc[x, 'geometry'].difference(
            isochrone_polys.loc[x+1, 'geometry'])
    isochrone_polys['color'] = colors
    for x in range(len(isochrone_polys)):
        folium.GeoJson(isochrone_polys.iloc[[x]],
                       style_function=style).add_to(map)
    folium.LayerControl().add_to(map)
    return map

for i in range(len(network_type)):
    get_folium_isochrone_map(Gs[i], place, trip_times, colors).save("../viz/isochrones/poly"+
                                                                network_type[i]+"/"+str(
                                                                schools.loc[index,'index'])+".html")
# %%

# %%

# Iterates over the schools and generates 3 isochrones: walk, bike and drive
def generate_route_isochrones(df):
    for index in list(df.index)[229:]:
        try:
            # Configure the place, network type, trip times, and travel speed
            place = schools.loc[index, 'geometry']
            Gs = [get_graph(place, x) for x in network_type]
            for i in range(len(network_type)):
                get_folium_route_time_distance_map(Gs[i], place, trip_times, colors).save("../viz/isochrones/route/"+
                                                                    network_type[i]+"/"+str(
                                                                    schools.loc[index,'index'])+".html")
        except ValueError:
            print(index)
            continue
        
generate_route_isochrones(schools)

#%%
# Create polygons and add some markers for POIs
place = schools.loc[44, 'geometry']
G = get_graph(place,'bike')
get_folium_route_time_distance_map(G, place, trip_times, colors)