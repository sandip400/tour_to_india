from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
import base64
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import markdown, math, datetime
import os, re, requests
import json, time, logging
from django.conf import settings
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from openrouteservice import Client, exceptions
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from openrouteservice import Client, exceptions
import polyline
import traceback
from django.urls import reverse
import google.generativeai as genai
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import tempfile
from pathlib import Path

# Load environment variables
load_dotenv()

# Set API keys
os.environ["TAVILY_API_KEY"] = "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"
os.environ["GOOGLE_API_KEY"] = "AIzaSyB4QwG3zKnXUOA8gkV_6myyL3p9YO2zFAA"
OPENWEATHERMAP_API_KEY = "d7edd1c7c5c73e1e693aa419a317ed2e"
ORS_API_KEY = os.getenv("ORS_API_KEY", "5b3ce3597851110001cf6248a8144657abb64a22af9c84eeb34a9f66")

ROUTES = [
    {"name": "home", "url": "/"},
    {"name": "ai trip", "url": "/AI_trip/"},
    {"name": "ai trip planner", "url": "/AI_trip/"},
    {"name": "trip planner", "url": "/AI_trip/"},
    {"name": "clickable map", "url": "/clickablemap/"},
    {"name": "interactive map", "url": "/clickablemap/"},
    {"name": "map", "url": "/clickablemap/"},
    {"name": "west bengal", "url": "/westbengal/"},
    {"name": "uttar pradesh", "url": "/uttarpradesh/"},
    {"name": "maharashtra", "url": "/maharashtra/"},
    {"name": "mumbai", "url": "/maharashtra/"},
    {"name": "rajasthan", "url": "/rajasthan/"},
    {"name": "andhra pradesh", "url": "/andhrapradesh/"},
    {"name": "jammu and kashmir", "url": "/jammuandkashmir/"},
    {"name": "kashmir", "url": "/jammuandkashmir/"},
    {"name": "goa", "url": "/goa/"},
    {"name": "kerala", "url": "/kerala/"},
    {"name": "tamil nadu", "url": "/tamilnadu/"},
    {"name": "karnataka", "url": "/Karnataka/"},
    {"name": "punjab", "url": "/punjab/"},
    {"name": "about", "url": "/about/"},
    {"name": "himachal pradesh", "url": "/himachalpradesh/"},
]

# Initialize logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

genai.configure(api_key="AIzaSyB4QwG3zKnXUOA8gkV_6myyL3p9YO2zFAA")

# Initialize Tavily and Gemini
search = TavilySearchResults(max_results=5)
model = init_chat_model("gemini-2.5-flash-preview-04-17", model_provider="google_genai")

# Enhanced coordinates database for Indian locations
INDIAN_COORDINATES = {
    # Major Cities
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "ahmedabad": (23.0225, 72.5714),
    "pune": (18.5204, 73.8567),
    "surat": (21.1702, 72.8311),
    "kanpur": (26.4499, 80.3319),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462),
    "nagpur": (21.1458, 79.0882),
    "indore": (22.7196, 75.8577),
    "thane": (19.2183, 72.9781),
    "bhopal": (23.2599, 77.4126),
    "visakhapatnam": (17.6868, 83.2185),
    "pimpri-chinchwad": (18.6298, 73.7997),
    "patna": (25.5941, 85.1376),
    "vadodara": (22.3072, 73.1812),
    "ghaziabad": (28.6692, 77.4538),
    "ludhiana": (30.9010, 75.8573),
    "agra": (27.1767, 78.0081),
    "nashik": (19.9975, 73.7898),
    "faridabad": (28.4089, 77.3178),
    "meerut": (28.9845, 77.7064),
    "rajkot": (22.3039, 70.8022),
    "kalyan-dombivli": (19.2403, 73.1305),
    "vasai-virar": (19.4912, 72.8054),
    "varanasi": (25.3176, 83.0062),
    "srinagar": (34.0837, 74.7973),
    "aurangabad": (19.8762, 75.3433),
    "dhanbad": (23.7957, 86.4304),
    "amritsar": (31.6340, 74.8723),
    "navi mumbai": (19.0330, 73.0297),
    "allahabad": (25.4358, 81.8463),
    "prayagraj": (25.4358, 81.8463),
    "ranchi": (23.3441, 85.3096),
    "howrah": (22.5958, 88.2636),
    "coimbatore": (11.0168, 76.9558),
    "jabalpur": (23.1815, 79.9864),
    "gwalior": (26.2183, 78.1828),
    "vijayawada": (16.5062, 80.6480),
    "jodhpur": (26.2389, 73.0243),
    "madurai": (9.9252, 78.1198),
    "raipur": (21.2514, 81.6296),
    "kota": (25.2138, 75.8648),
    "chandigarh": (30.7333, 76.7794),
    "guwahati": (26.1445, 91.7362),
    "solapur": (17.6599, 75.9064),
    "hubli-dharwad": (15.3647, 75.1240),
    "bareilly": (28.3670, 79.4304),
    "moradabad": (28.8386, 78.7733),
    "mysore": (12.2958, 76.6394),
    "mysuru": (12.2958, 76.6394),
    "gurgaon": (28.4595, 77.0266),
    "gurugram": (28.4595, 77.0266),
    "aligarh": (27.8974, 78.0880),
    "jalandhar": (31.3260, 75.5762),
    "tiruchirappalli": (10.7905, 78.7047),
    "bhubaneswar": (20.2961, 85.8245),
    "salem": (11.6643, 78.1460),
    "warangal": (17.9689, 79.5941),
    "mira-bhayandar": (19.2952, 72.8544),
    "thiruvananthapuram": (8.5241, 76.9366),
    "bhiwandi": (19.3002, 73.0635),
    "saharanpur": (29.9680, 77.5552),
    "guntur": (16.3067, 80.4365),
    "amravati": (20.9374, 77.7796),
    "bikaner": (28.0229, 73.3119),
    "noida": (28.5355, 77.3910),
    "jamshedpur": (22.8046, 86.2029),
    "bhilai nagar": (21.1938, 81.3509),
    "cuttack": (20.4625, 85.8828),
    "firozabad": (27.1592, 78.3957),
    "kochi": (9.9312, 76.2673),
    "cochin": (9.9312, 76.2673),
    "bhavnagar": (21.7645, 72.1519),
    "dehradun": (30.3165, 78.0322),
    "durgapur": (23.4800, 87.3119),
    "asansol": (23.6739, 86.9524),
    "nanded": (19.1383, 77.2975),
    "kolhapur": (16.7050, 74.2433),
    "ajmer": (26.4499, 74.6399),
    "akola": (20.7002, 77.0082),
    "gulbarga": (17.3297, 76.8343),
    "jamnagar": (22.4707, 70.0577),
    "ujjain": (23.1765, 75.7885),
    "loni": (28.7333, 77.2833),
    "siliguri": (26.7271, 88.3953),
    "jhansi": (25.4484, 78.5685),
    "ulhasnagar": (19.2215, 73.1645),
    "jammu": (32.7266, 74.8570),
    "sangli-miraj & kupwad": (16.8524, 74.5815),
    "mangalore": (12.9141, 74.8560),
    "erode": (11.3410, 77.7172),
    "belgaum": (15.8497, 74.4977),
    "ambattur": (13.1143, 80.1548),
    "tirunelveli": (8.7139, 77.7567),
    "malegaon": (20.5579, 74.5287),
    "gaya": (24.7914, 85.0002),
    "jalgaon": (21.0077, 75.5626),
    "udaipur": (24.5854, 73.7125),
    "maheshtala": (22.4978, 88.2476),
    
    # Tourist Destinations
    "goa": (15.2993, 74.1240),
    "shimla": (31.1048, 77.1734),
    "manali": (32.2396, 77.1887),
    "darjeeling": (27.0410, 88.2663),
    "ooty": (11.4064, 76.6932),
    "kodaikanal": (10.2381, 77.4892),
    "munnar": (10.0889, 77.0595),
    "rishikesh": (30.0869, 78.2676),
    "haridwar": (29.9457, 78.1642),
    "pushkar": (26.4899, 74.5511),
    "mount abu": (24.5925, 72.7156),
    "nainital": (29.3803, 79.4636),
    "mussoorie": (30.4598, 78.0664),
    "kasauli": (30.8977, 76.9651),
    "dalhousie": (32.5448, 75.9618),
    "mcleod ganj": (32.2190, 76.3234),
    "dharamshala": (32.2190, 76.3234),
    "leh": (34.1526, 77.5771),
    "ladakh": (34.2996, 77.2932),
    "srinagar": (34.0837, 74.7973),
    "gulmarg": (34.0484, 74.3803),
    "pahalgam": (34.0173, 75.3317),
    "sonamarg": (34.2996, 75.2917),
    "khajuraho": (24.8318, 79.9199),
    "hampi": (15.3350, 76.4600),
    "badami": (15.9149, 75.6767),
    "aihole": (15.9537, 75.8012),
    "pattadakal": (15.9447, 75.8174),
    "mahabalipuram": (12.6269, 80.1927),
    "pondicherry": (11.9416, 79.8083),
    "puducherry": (11.9416, 79.8083),
    "auroville": (11.9988, 79.8081),
    "rameswaram": (9.2876, 79.3129),
    "kanyakumari": (8.0883, 77.5385),
    "alleppey": (9.4981, 76.3388),
    "alappuzha": (9.4981, 76.3388),
    "kumarakom": (9.6178, 76.4298),
    "thekkady": (9.5916, 77.1603),
    "periyar": (9.5916, 77.1603),
    "wayanad": (11.6854, 76.1320),
    "kovalam": (8.4004, 76.9784),
    "varkala": (8.7379, 76.7163),
    "andaman": (11.7401, 92.6586),
    "port blair": (11.6234, 92.7265),
    "havelock": (12.0067, 93.0019),
    "neil island": (11.8169, 93.0499),
    "lakshadweep": (10.5667, 72.6417),
    "diu": (20.7144, 70.9876),
    "daman": (20.3974, 72.8328),
    "silvassa": (20.2738, 73.0135),
    
    # Heritage Sites
    "taj mahal": (27.1751, 78.0421),
    "red fort": (28.6562, 77.2410),
    "qutub minar": (28.5245, 77.1855),
    "india gate": (28.6129, 77.2295),
    "lotus temple": (28.5535, 77.2588),
    "humayun tomb": (28.5933, 77.2507),
    "fatehpur sikri": (27.0945, 77.6619),
    "amber fort": (26.9855, 75.8513),
    "hawa mahal": (26.9239, 75.8267),
    "city palace jaipur": (26.9255, 75.8235),
    "jantar mantar": (26.9246, 75.8249),
    "mehrangarh fort": (26.2971, 73.0187),
    "umaid bhawan palace": (26.2884, 73.0394),
    "jaswant thada": (26.2971, 73.0187),
    "golden temple": (31.6200, 74.8765),
    "jallianwala bagh": (31.6205, 74.8792),
    "wagah border": (31.6045, 74.5735),
    "mysore palace": (12.3051, 76.6551),
    "tipu sultan palace": (12.9591, 77.5750),
    "gol gumbaz": (16.8302, 75.7138),
    "charminar": (17.3616, 78.4747),
    "golconda fort": (17.3833, 78.4011),
    "salar jung museum": (17.3713, 78.4804),
    "gateway of india": (18.9220, 72.8347),
    "elephanta caves": (18.9633, 72.9315),
    "ajanta caves": (20.5519, 75.7033),
    "ellora caves": (20.0269, 75.1791),
    "shirdi": (19.7645, 74.4769),
    "somnath": (20.8880, 70.4017),
    "dwarka": (22.2394, 68.9678),
    "rann of kutch": (23.7337, 69.8597),
    "statue of unity": (21.8380, 73.7191),
    "sabarmati ashram": (23.0615, 72.5797),
    "akshardham delhi": (28.6127, 77.2773),
    "akshardham gandhinagar": (23.2156, 72.6369),
    "sun temple konark": (19.8876, 86.0945),
    "jagannath temple": (19.8135, 85.8312),
    "lingaraj temple": (20.2379, 85.8338),
    "chilika lake": (19.7165, 85.3206),
    "puri": (19.8135, 85.8312),
    "konark": (19.8876, 86.0945),
    "sanchi stupa": (23.4793, 77.7398),
    "bhimbetka": (22.9373, 77.6100),
    "mandu": (22.3647, 75.3971),
    "orchha": (25.3518, 78.6418),
    "gwalior fort": (26.2295, 78.1691),
    "khajuraho temples": (24.8318, 79.9199),
    "bandhavgarh": (23.7069, 81.0169),
    "kanha": (22.3344, 80.6119),
    "pench": (21.7679, 79.2961),
    "tadoba": (20.2180, 79.3430),
    "ranthambore": (26.0173, 76.5026),
    "sariska": (27.3389, 76.4063),
    "bharatpur": (27.2152, 77.4909),
    "keoladeo": (27.1594, 77.5226),
    "corbett": (29.5316, 78.9463),
    "jim corbett": (29.5316, 78.9463),
    "rajaji": (30.0581, 78.2676),
    "valley of flowers": (30.7268, 79.6005),
    "hemkund sahib": (30.7268, 79.6005),
    "badrinath": (30.7433, 79.4938),
    "kedarnath": (30.7346, 79.0669),
    "gangotri": (30.9993, 78.9411),
    "yamunotri": (31.0117, 78.4270),
    "char dham": (30.7433, 79.4938),
    "amarnath": (34.1341, 75.2711),
    "vaishno devi": (33.0307, 74.9496),
    "hemis": (34.2685, 77.6194),
    "thiksey": (34.2685, 77.6194),
    "pangong tso": (33.7500, 78.9500),
    "nubra valley": (34.5539, 77.5397),
    "tso moriri": (32.9057, 78.3142),
    "magnetic hill": (34.2996, 77.2932),
    "spituk": (34.1526, 77.5771),
    "shanti stupa": (34.1526, 77.5771),
    "leh palace": (34.1642, 77.5840),
    "zanskar": (33.4500, 76.8900),
    "kargil": (34.5539, 76.1320),
    "drass": (34.4167, 75.7500),
    "siachen": (35.4219, 77.1025),
    
    # Hill Stations
    "mount abu": (24.5925, 72.7156),
    "saputara": (20.5970, 73.7500),
    "matheran": (18.9847, 73.2673),
    "lonavala": (18.7537, 73.4068),
    "khandala": (18.7645, 73.3869),
    "mahabaleshwar": (17.9244, 73.6544),
    "panchgani": (17.9244, 73.8009),
    "amboli": (15.9581, 74.0064),
    "chikmangalur": (13.3161, 75.7720),
    "coorg": (12.3375, 75.8069),
    "madikeri": (12.4244, 75.7382),
    "sakleshpur": (12.9441, 75.7847),
    "yercaud": (11.7753, 78.2186),
    "yelagiri": (12.5810, 78.6548),
    "horsley hills": (13.6667, 78.4000),
    "araku valley": (18.3273, 82.8739),
    "lambasingi": (17.9500, 82.5833),
    "ananthagiri hills": (17.5500, 77.9000),
    "pachmarhi": (22.4676, 78.4336),
    "amarkantak": (22.6792, 81.4592),
    "chitrakoot": (25.2009, 80.8848),
    "shivpuri": (25.4233, 77.6581),
    "ranikhet": (29.6436, 79.4322),
    "almora": (29.5971, 79.6590),
    "bageshwar": (29.8390, 79.7737),
    "pithoragarh": (29.5830, 80.2184),
    "lansdowne": (29.8372, 78.6869),
    "auli": (30.5200, 79.5600),
    "chopta": (30.4500, 79.1167),
    "tungnath": (30.4896, 79.2124),
    "chandrashila": (30.4896, 79.2124),
    "kedarkantha": (31.0200, 78.3200),
    "har ki dun": (31.1167, 78.2167),
    "dayara bugyal": (30.8667, 78.5833),
    "roopkund": (30.2833, 79.7333),
    "brahmatal": (30.4167, 79.6167),
    "kuari pass": (30.6167, 79.5833),
    "gomukh": (30.9289, 79.0831),
    "tapovan": (30.9500, 79.0833),
    "satopanth": (30.8833, 79.3167),
    "vasuki tal": (30.8833, 79.2167),
    "mana village": (30.7500, 79.4667),
    "malari": (30.3167, 79.9167),
    "niti village": (30.8167, 79.8833),
    
    # Beaches
    "goa beaches": (15.2993, 74.1240),
    "baga beach": (15.5560, 73.7516),
    "calangute beach": (15.5438, 73.7553),
    "anjuna beach": (15.5732, 73.7395),
    "vagator beach": (15.6094, 73.7346),
    "arambol beach": (15.6869, 73.7026),
    "morjim beach": (15.6347, 73.7185),
    "ashwem beach": (15.6594, 73.7115),
    "mandrem beach": (15.6594, 73.7115),
    "candolim beach": (15.5167, 73.7667),
    "sinquerim beach": (15.5167, 73.7667),
    "dona paula": (15.4589, 73.8067),
    "miramar beach": (15.4589, 73.8067),
    "colva beach": (15.2799, 73.9111),
    "benaulim beach": (15.2533, 73.9244),
    "varca beach": (15.2167, 73.9333),
    "cavelossim beach": (15.1667, 73.9500),
    "mobor beach": (15.1500, 73.9667),
    "betalbatim beach": (15.2667, 73.9167),
    "majorda beach": (15.2833, 73.9000),
    "utorda beach": (15.3000, 73.8833),
    "arossim beach": (15.2500, 73.9333),
    "velsao beach": (15.3333, 73.8500),
    "bogmalo beach": (15.3500, 73.8333),
    "hollant beach": (15.3667, 73.8167),
    "cansaulim beach": (15.3833, 73.8000),
    "marina beach": (13.0500, 80.2824),
    "elliot beach": (12.9915, 80.2668),
    "mahabalipuram beach": (12.6269, 80.1927),
    "pondicherry beach": (11.9416, 79.8083),
    "paradise beach": (11.9416, 79.8083),
    "auroville beach": (11.9988, 79.8081),
    "cuddalore beach": (11.7480, 79.7714),
    "tranquebar beach": (11.0333, 79.8500),
    "poompuhar beach": (11.1500, 79.8500),
    "nagapattinam beach": (10.7658, 79.8448),
    "velankanni beach": (10.6833, 79.8333),
    "rameswaram beach": (9.2876, 79.3129),
    "dhanushkodi beach": (9.1667, 79.4167),
    "kanyakumari beach": (8.0883, 77.5385),
    "kovalam beach": (8.4004, 76.9784),
    "lighthouse beach": (8.4004, 76.9784),
    "hawah beach": (8.4004, 76.9784),
    "samudra beach": (8.4004, 76.9784),
    "varkala beach": (8.7379, 76.7163),
    "papanasam beach": (8.7379, 76.7163),
    "black beach": (8.7379, 76.7163),
    "alappuzha beach": (9.4981, 76.3388),
    "marari beach": (9.6000, 76.3000),
    "andhakaranazhi beach": (9.5500, 76.3500),
    "cherai beach": (10.1167, 76.1833),
    "fort kochi beach": (9.9658, 76.2422),
    "vypin beach": (10.1167, 76.1833),
    "munambam beach": (10.1833, 76.1667),
    "bekal beach": (12.3833, 75.0333),
    "kasaragod beach": (12.4996, 74.9869),
    "karwar beach": (14.8167, 74.1333),
    "gokarna beach": (14.5500, 74.3167),
    "om beach": (14.5333, 74.3167),
    "kudle beach": (14.5333, 74.3167),
    "half moon beach": (14.5333, 74.3167),
    "paradise beach gokarna": (14.5333, 74.3167),
    "murudeshwar beach": (14.0942, 74.4842),
    "udupi beach": (13.3409, 74.7421),
    "malpe beach": (13.3500, 74.7000),
    "kaup beach": (13.2167, 74.7500),
    "surathkal beach": (13.0167, 74.7833),
    "panambur beach": (12.9500, 74.8167),
    "tannirbhavi beach": (12.9167, 74.8333),
    "ullal beach": (12.8000, 74.8667),
    "someshwar beach": (12.7833, 74.8833),
    "radhanagar beach": (11.9833, 92.9500),
    "elephant beach": (12.0167, 93.0000),
    "vijaynagar beach": (12.0500, 92.9833),
    "kalapathar beach": (11.9500, 92.9667),
    "corbyn cove": (11.6500, 92.7333),
    "wandoor beach": (11.5833, 92.6167),
    "red skin island": (11.5500, 92.6000),
    "jolly buoy island": (11.5167, 92.5833),
    "ross island": (11.6833, 92.7667),
    "viper island": (11.6667, 92.7500),
    "chatham island": (11.6833, 92.7500),
    "barren island": (12.2833, 93.8500),
    "narcondam island": (13.4333, 94.2833),
    "little andaman": (10.7500, 92.5000),
    "car nicobar": (9.1667, 92.8167),
    "great nicobar": (7.0000, 93.9167),
    "kavaratti": (10.5667, 72.6417),
    "agatti": (10.8500, 72.1833),
    "bangaram": (10.9333, 72.2833),
    "kadmat": (11.2167, 72.7833),
    "kalpeni": (10.0833, 73.6500),
    "minicoy": (8.2833, 73.0500),
    "thinnakara": (10.9167, 72.2667),
    "parali": (10.9000, 72.2500),
    "suheli": (10.0833, 72.0833),
    "cheriyam": (11.0500, 72.7167),
    "pitti": (11.1167, 72.0833),
    
    # States and Union Territories
    "andhra pradesh": (15.9129, 79.7400),
    "arunachal pradesh": (28.2180, 94.7278),
    "assam": (26.2006, 92.9376),
    "bihar": (25.0961, 85.3131),
    "chhattisgarh": (21.2787, 81.8661),
    "gujarat": (23.0225, 72.5714),
    "haryana": (29.0588, 76.0856),
    "himachal pradesh": (31.1048, 77.1734),
    "jharkhand": (23.6102, 85.2799),
    "karnataka": (15.3173, 75.7139),
    "kerala": (10.8505, 76.2711),
    "madhya pradesh": (22.9734, 78.6569),
    "maharashtra": (19.7515, 75.7139),
    "manipur": (24.6637, 93.9063),
    "meghalaya": (25.4670, 91.3662),
    "mizoram": (23.1645, 92.9376),
    "nagaland": (26.1584, 94.5624),
    "odisha": (20.9517, 85.0985),
    "punjab": (31.1471, 75.3412),
    "rajasthan": (27.0238, 74.2179),
    "sikkim": (27.5330, 88.5122),
    "tamil nadu": (11.1271, 78.6569),
    "telangana": (18.1124, 79.0193),
    "tripura": (23.9408, 91.9882),
    "uttar pradesh": (26.8467, 80.9462),
    "uttarakhand": (30.0668, 79.0193),
    "west bengal": (22.9868, 87.8550),
    "andaman and nicobar islands": (11.7401, 92.6586),
    "dadra and nagar haveli": (20.1809, 73.0169),
    "daman and diu": (20.4283, 72.8397),
    "lakshadweep": (10.5667, 72.6417),
    "puducherry": (11.9416, 79.8083),
    "ladakh": (34.2996, 77.2932),
    "jammu and kashmir": (34.0837, 74.7973),
    
    # Additional popular destinations
    "thar desert": (26.9167, 70.9000),
    "great rann of kutch": (23.7337, 69.8597),
    "little rann of kutch": (23.4167, 71.0833),
    "sundarbans": (21.9497, 88.4297),
    "kaziranga": (26.5775, 93.1714),
    "manas": (26.7050, 90.9614),
    "dibru saikhowa": (27.5833, 95.1667),
    "nameri": (26.9167, 92.8333),
    "orang": (26.6333, 92.3167),
    "pobitora": (26.2500, 91.9833),
    "garampani": (26.1833, 93.0167),
    "gibbon": (27.1667, 94.3833),
    "dehing patkai": (27.3000, 95.5000),
    "namdapha": (27.5167, 96.3500),
    "mouling": (28.3667, 95.1667),
    "pakke": (27.1000, 92.9000),
    "eaglenest": (27.1167, 92.4167),
    "sessa orchid": (27.2333, 92.5000),
    "itanagar": (27.0844, 93.6053),
    "tawang": (27.5858, 91.8717),
    "bomdila": (27.2667, 92.4167),
    "ziro": (27.5500, 93.8333),
    "along": (28.1667, 94.7833),
    "pasighat": (28.0667, 95.3333),
    "roing": (28.1167, 95.8500),
    "tezu": (27.9167, 96.1667),
    "namsai": (27.8000, 95.7667),
    "changlang": (27.1500, 95.7333),
    "khonsa": (26.9833, 95.0167),
    "longding": (26.7833, 95.2333),
    "tirap": (26.9167, 95.3333),
    "anjaw": (28.0833, 96.7500),
    "lohit": (27.9833, 96.2167),
    "dibang valley": (28.7500, 95.7500),
    "upper dibang valley": (28.8333, 95.8333),
    "west kameng": (27.3333, 92.4167),
    "east kameng": (27.2167, 93.0000),
    "papum pare": (27.1167, 93.6167),
    "kurung kumey": (27.8833, 93.4167),
    "kra daadi": (27.5333, 93.2833),
    "lower subansiri": (27.8333, 94.0000),
    "upper subansiri": (28.1167, 94.0833),
    "west siang": (28.4167, 94.6500),
    "east siang": (28.0833, 95.3333),
    "siang": (28.7500, 95.0000),
    "upper siang": (28.8333, 95.3333),
    "tawang monastery": (27.5858, 91.8717),
    "bumla pass": (27.5500, 91.7833),
    "sela pass": (27.5833, 92.0667),
    "nuranang falls": (27.5667, 92.0167),
    "madhuri lake": (27.5500, 92.0000),
    "jaswantgarh": (27.5833, 92.0500),
    "dirang": (27.3500, 92.2167),
    "sangti valley": (27.2833, 92.4000),
    "mandala top": (27.2667, 92.4167),
    "gorichen peak": (27.6833, 92.2167),
    "taktsang gompa": (27.5833, 91.8833),
    "urgelling monastery": (27.5833, 91.8833),
    "ani gompa": (27.5833, 91.8833),
    "gyangong ani gompa": (27.5833, 91.8833),
    "khinmey monastery": (27.5833, 91.8833),
    "thongdrol": (27.5833, 91.8833),
    "war memorial tawang": (27.5833, 91.8833),
    "craft centre tawang": (27.5833, 91.8833),
    "tawang chu": (27.5833, 91.8833),
    "p.t.tso lake": (27.5833, 91.8833),
    "shonga tser lake": (27.5833, 91.8833),
    "brahmadung chung": (27.5833, 91.8833),
    "mukto": (27.5833, 91.8833),
    "zemithang": (27.6167, 91.8167),
    "lumla": (27.5167, 91.8333),
    "jang": (27.4833, 91.8667),
    "kitpi": (27.4500, 91.9000),
    "dudunghar": (27.4167, 91.9333),
    "mukto": (27.3833, 91.9667),
    "thingbu": (27.3500, 92.0000),
    "nafra": (27.3167, 92.0333),
    "thembang": (27.2833, 92.0667),
    "rupa": (27.2500, 92.1000),
    "kalaktang": (27.2167, 92.1333),
    "shergaon": (27.1833, 92.1667),
    "rahung": (27.1500, 92.2000),
    "dirang dzong": (27.3500, 92.2167),
    "sangti": (27.2833, 92.4000),
    "tenga": (27.2500, 92.4333),
    "bhalukpong": (26.8500, 92.6333),
    "tipi": (26.8167, 92.6667),
    "khellong": (26.7833, 92.7000),
    "seppa": (27.2833, 93.0000),
    "chayang tajo": (27.2500, 93.0333),
    "pakke kessang": (27.2167, 93.0667),
    "seijosa": (27.1833, 93.1000),
    "richukrong": (27.1500, 93.1333),
    "kimin": (27.1167, 93.1667),
    "balijan": (27.0833, 93.2000),
    "naharlagun": (27.1000, 93.7000),
    "nirjuli": (27.0833, 93.7333),
    "doimukh": (27.0500, 93.7667),
    "sagalee": (27.0167, 93.8000),
    "mengio": (26.9833, 93.8333),
    "kimin": (26.9500, 93.8667),
    "palin": (27.6333, 93.6667),
    "chambang": (27.6000, 93.7000),
    "dollungmukh": (27.5667, 93.7333),
    "koloriang": (27.9167, 93.4167),
    "sarli": (27.8833, 93.4500),
    "nyapin": (27.8500, 93.4833),
    "damin": (27.8167, 93.5167),
    "palin": (27.7833, 93.5500),
    "chambang": (27.7500, 93.5833),
    "dollungmukh": (27.7167, 93.6167),
    "sangram": (27.6833, 93.6500),
    "kurung kumey": (27.6500, 93.6833),
    "pipsorang": (27.6167, 93.7167),
    "tali": (27.5833, 93.7500),
    "yachuli": (27.8667, 94.0333),
    "ziro": (27.5500, 93.8333),
    "hapoli": (27.5833, 93.8167),
    "hong": (27.6167, 93.8000),
    "hari": (27.6500, 93.7833),
    "dutta": (27.6833, 93.7667),
    "raga": (27.7167, 93.7500),
    "yazali": (27.7500, 93.7333),
    "chambang": (27.7833, 93.7167),
    "dollungmukh": (27.8167, 93.7000),
    "sangram": (27.8500, 93.6833),
    "kurung kumey": (27.8833, 93.6667),
    "pipsorang": (27.9167, 93.6500),
    "tali": (27.9500, 93.6333),
    "yachuli": (27.9833, 93.6167),
    "ziro": (28.0167, 93.6000),
    "hapoli": (28.0500, 93.5833),
    "hong": (28.0833, 93.5667),
    "hari": (28.1167, 93.5500),
    "dutta": (28.1500, 93.5333),
    "raga": (28.1833, 93.5167),
    "yazali": (28.2167, 93.5000),
    "chambang": (28.2500, 93.4833),
    "dollungmukh": (28.2833, 93.4667),
    "sangram": (28.3167, 93.4500),
    "kurung kumey": (28.3500, 93.4333),
    "pipsorang": (28.3833, 93.4167),
    "tali": (28.4167, 93.4000),
    "yachuli": (28.4500, 93.3833),
    "ziro": (28.4833, 93.3667),
    "hapoli": (28.5167, 93.3500),
    "hong": (28.5500, 93.3333),
    "hari": (28.5833, 93.3167),
    "dutta": (28.6167, 93.3000),
    "raga": (28.6500, 93.2833),
    "yazali": (28.6833, 93.2667),
    "chambang": (28.7167, 93.2500),
    "dollungmukh": (28.7500, 93.2333),
    "sangram": (28.7833, 93.2167),
    "kurung kumey": (28.8167, 93.2000),
    "pipsorang": (28.8500, 93.1833),
    "tali": (28.8833, 93.1667),
    "yachuli": (28.9167, 93.1500),
    "ziro": (28.9500, 93.1333),
    "hapoli": (28.9833, 93.1167),
    "hong": (29.0167, 93.1000),
    "hari": (29.0500, 93.0833),
    "dutta": (29.0833, 93.0667),
    "raga": (29.1167, 93.0500),
    "yazali": (29.1500, 93.0333),
    "chambang": (29.1833, 93.0167),
    "dollungmukh": (29.2167, 93.0000),
    "sangram": (29.2500, 92.9833),
    "kurung kumey": (29.2833, 92.9667),
    "pipsorang": (29.3167, 92.9500),
    "tali": (29.3500, 92.9333),
    "yachuli": (29.3833, 92.9167),
    "ziro": (29.4167, 92.9000),
    "hapoli": (29.4500, 92.8833),
    "hong": (29.4833, 92.8667),
    "hari": (29.5167, 92.8500),
    "dutta": (29.5500, 92.8333),
    "raga": (29.5833, 92.8167),
    "yazali": (29.6167, 92.8000),
    "chambang": (29.6500, 92.7833),
    "dollungmukh": (29.6833, 92.7667),
    "sangram": (29.7167, 92.7500),
    "kurung kumey": (29.7500, 92.7333),
    "pipsorang": (29.7833, 92.7167),
    "tali": (29.8167, 92.7000),
    "yachuli": (29.8500, 92.6833),
    "ziro": (29.8833, 92.6667),
    "hapoli": (29.9167, 92.6500),
    "hong": (29.9500, 92.6333),
    "hari": (29.9833, 92.6167),
    "dutta": (30.0167, 92.6000),
    "raga": (30.0500, 92.5833),
    "yazali": (30.0833, 92.5667),
    "chambang": (30.1167, 92.5500),
    "dollungmukh": (30.1500, 92.5333),
    "sangram": (30.1833, 92.5167),
    "kurung kumey": (30.2167, 92.5000),
    "pipsorang": (30.2500, 92.4833),
    "tali": (30.2833, 92.4667),
    "yachuli": (30.3167, 92.4500),
    "ziro": (30.3500, 92.4333),
    "hapoli": (30.3833, 92.4167),
    "hong": (30.4167, 92.4000),
    "hari": (30.4500, 92.3833),
    "dutta": (30.4833, 92.3667),
    "raga": (30.5167, 92.3500),
    "yazali": (30.5500, 92.3333),
    "chambang": (30.5833, 92.3167),
    "dollungmukh": (30.6167, 92.3000),
    "sangram": (30.6500, 92.2833),
    "kurung kumey": (30.6833, 92.2667),
    "pipsorang": (30.7167, 92.2500),
    "tali": (30.7500, 92.2333),
    "yachuli": (30.7833, 92.2167),
    "ziro": (30.8167, 92.2000),
    "hapoli": (30.8500, 92.1833),
    "hong": (30.8833, 92.1667),
    "hari": (30.9167, 92.1500),
    "dutta": (30.9500, 92.1333),
    "raga": (30.9833, 92.1167),
    "yazali": (31.0167, 92.1000),
    "chambang": (31.0500, 92.0833),
    "dollungmukh": (31.0833, 92.0667),
    "sangram": (31.1167, 92.0500),
    "kurung kumey": (31.1500, 92.0333),
    "pipsorang": (31.1833, 92.0167),
    "tali": (31.2167, 92.0000),
    "yachuli": (31.2500, 91.9833),
    "ziro": (31.2833, 91.9667),
    "hapoli": (31.3167, 91.9500),
    "hong": (31.3500, 91.9333),
    "hari": (31.3833, 91.9167),
    "dutta": (31.4167, 91.9000),
    "raga": (31.4500, 91.8833),
    "yazali": (31.4833, 91.8667),
    "chambang": (31.5167, 91.8500),
    "dollungmukh": (31.5500, 91.8333),
    "sangram": (31.5833, 91.8167),
    "kurung kumey": (31.6167, 91.8000),
    "pipsorang": (31.6500, 91.7833),
    "tali": (31.6833, 91.7667),
    "yachuli": (31.7167, 91.7500),
    "ziro": (31.7500, 91.7333),
    "hapoli": (31.7833, 91.7167),
    "hong": (31.8167, 91.7000),
    "hari": (31.8500, 91.6833),
    "dutta": (31.8833, 91.6667),
    "raga": (31.9167, 91.6500),
    "yazali": (31.9500, 91.6333),
    "chambang": (31.9833, 91.6167),
    "dollungmukh": (32.0167, 91.6000),
    "sangram": (32.0500, 91.5833),
    "kurung kumey": (32.0833, 91.5667),
    "pipsorang": (32.1167, 91.5500),
    "tali": (32.1500, 91.5333),
    "yachuli": (32.1833, 91.5167),
    "ziro": (32.2167, 91.5000),
    "hapoli": (32.2500, 91.4833),
    "hong": (32.2833, 91.4667),
    "hari": (32.3167, 91.4500),
    "dutta": (32.3500, 91.4333),
    "raga": (32.3833, 91.4167),
    "yazali": (32.4167, 91.4000),
    "chambang": (32.4500, 91.3833),
    "dollungmukh": (32.4833, 91.3667),
    "sangram": (32.5167, 91.3500),
    "kurung kumey": (32.5500, 91.3333),
    "pipsorang": (32.5833, 91.3167),
    "tali": (32.6167, 91.3000),
    "yachuli": (32.6500, 91.2833),
    "ziro": (32.6833, 91.2667),
    "hapoli": (32.7167, 91.2500),
    "hong": (32.7500, 91.2333),
    "hari": (32.7833, 91.2167),
    "dutta": (32.8167, 91.2000),
    "raga": (32.8500, 91.1833),
    "yazali": (32.8833, 91.1667),
    "chambang": (32.9167, 91.1500),
    "dollungmukh": (32.9500, 91.1333),
    "sangram": (32.9833, 91.1167),
    "kurung kumey": (33.0167, 91.1000),
    "pipsorang": (33.0500, 91.0833),
    "tali": (33.0833, 91.0667),
    "yachuli": (33.1167, 91.0500),
    "ziro": (33.1500, 91.0333),
    "hapoli": (33.1833, 91.0167),
    "hong": (33.2167, 91.0000),
    "hari": (33.2500, 90.9833),
    "dutta": (33.2833, 90.9667),
    "raga": (33.3167, 90.9500),
    "yazali": (33.3500, 90.9333),
    "chambang": (33.3833, 90.9167),
    "dollungmukh": (33.4167, 90.9000),
    "sangram": (33.4500, 90.8833),
    "kurung kumey": (33.4833, 90.8667),
    "pipsorang": (33.5167, 90.8500),
    "tali": (33.5500, 90.8333),
    "yachuli": (33.5833, 90.8167),
    "ziro": (33.6167, 90.8000),
    "hapoli": (33.6500, 90.7833),
    "hong": (33.6833, 90.7667),
    "hari": (33.7167, 90.7500),
    "dutta": (33.7500, 90.7333),
    "raga": (33.7833, 90.7167),
    "yazali": (33.8167, 90.7000),
    "chambang": (33.8500, 90.6833),
    "dollungmukh": (33.8833, 90.6667),
    "sangram": (33.9167, 90.6500),
    "kurung kumey": (33.9500, 90.6333),
    "pipsorang": (33.9833, 90.6167),
    "tali": (34.0167, 90.6000),
    "yachuli": (34.0500, 90.5833),
    "ziro": (34.0833, 90.5667),
    "hapoli": (34.1167, 90.5500),
    "hong": (34.1500, 90.5333),
    "hari": (34.1833, 90.5167),
    "dutta": (34.2167, 90.5000),
    "raga": (34.2500, 90.4833),
    "yazali": (34.2833, 90.4667),
    "chambang": (34.3167, 90.4500),
    "dollungmukh": (34.3500, 90.4333),
    "sangram": (34.3833, 90.4167),
    "kurung kumey": (34.4167, 90.4000),
    "pipsorang": (34.4500, 90.3833),
    "tali": (34.4833, 90.3667),
    "yachuli": (34.5167, 90.3500),
    "ziro": (34.5500, 90.3333),
    "hapoli": (34.5833, 90.3167),
    "hong": (34.6167, 90.3000),
    "hari": (34.6500, 90.2833),
    "dutta": (34.6833, 90.2667),
    "raga": (34.7167, 90.2500),
    "yazali": (34.7500, 90.2333),
    "chambang": (34.7833, 90.2167),
    "dollungmukh": (34.8167, 90.2000),
    "sangram": (34.8500, 90.1833),
    "kurung kumey": (34.8833, 90.1667),
    "pipsorang": (34.9167, 90.1500),
    "tali": (34.9500, 90.1333),
    "yachuli": (34.9833, 90.1167),
    "ziro": (35.0167, 90.1000),
    "hapoli": (35.0500, 90.0833),
    "hong": (35.0833, 90.0667),
    "hari": (35.1167, 90.0500),
    "dutta": (35.1500, 90.0333),
    "raga": (35.1833, 90.0167),
    "yazali": (35.2167, 90.0000),
}

# --- Helper Functions ---

def clean_json(response):
    """Clean JSON string from model output by removing markdown code fences."""
    cleaned = re.sub(r"\`\`\`json|\`\`\`", "", response).strip()
    return cleaned

def get_enhanced_coordinates(place_name):
    """Enhanced coordinate fetching with multiple fallback methods."""
    place_lower = place_name.lower().strip()
    
    # First check our comprehensive database
    if place_lower in INDIAN_COORDINATES:
        lat, lon = INDIAN_COORDINATES[place_lower]
        logger.info(f"Found coordinates for {place_name} in database: ({lat}, {lon})")
        return lat, lon
    
    # Try variations of the place name
    variations = [
        place_lower,
        place_lower.replace(" ", ""),
        place_lower.replace("-", " "),
        place_lower.replace("_", " "),
        place_lower + " india",
        place_lower.split()[0] if " " in place_lower else place_lower,
    ]
    
    for variation in variations:
        if variation in INDIAN_COORDINATES:
            lat, lon = INDIAN_COORDINATES[variation]
            logger.info(f"Found coordinates for {place_name} using variation '{variation}': ({lat}, {lon})")
            return lat, lon
    
    # Use Gemini to get coordinates with enhanced prompting
    try:
        coord_prompt = ChatPromptTemplate.from_template("""
        You are a geography expert specializing in Indian locations. Find the precise latitude and longitude coordinates for "{place}", India.
        
        IMPORTANT INSTRUCTIONS:
        1. Search for the exact location within India
        2. If it's a landmark, provide the coordinates of that specific landmark
        3. If it's a city/town, provide the city center coordinates
        4. If it's a region/area, provide the central coordinates
        5. Ensure coordinates are within India's boundaries (6°N to 37°N latitude, 68°E to 97°E longitude)
        
        Provide ONLY the coordinates in this exact format: "latitude,longitude"
        Example: "26.2389,73.0243"
        
        Do not include any other text, explanations, or formatting.
        """)
        
        coord_chain = coord_prompt | model | StrOutputParser()
        coord_response = coord_chain.invoke({"place": place_name})
        coords = coord_response.strip().split(',')
        
        if len(coords) == 2:
            try:
                lat = float(coords[0])
                lon = float(coords[1])
                # Validate coordinates are within India
                if 6 <= lat <= 37 and 68 <= lon <= 98:
                    logger.info(f"Gemini found coordinates for {place_name}: ({lat}, {lon})")
                    return lat, lon
                else:
                    logger.warning(f"Gemini coordinates for {place_name} are outside India: ({lat}, {lon})")
            except ValueError:
                logger.error(f"Invalid coordinate format from Gemini for {place_name}: {coord_response}")
    except Exception as e:
        logger.error(f"Error getting coordinates from Gemini for {place_name}: {e}")
    
    # Use Tavily search as final fallback
    try:
        search_query = f"{place_name} India latitude longitude coordinates location"
        search_results = search.invoke(search_query)
        
        for result in search_results:
            content = result.get('content', '').lower()
            # Look for coordinate patterns in search results
            coord_patterns = [
                r'(\d+\.?\d*)[°\s]*n[,\s]*(\d+\.?\d*)[°\s]*e',
                r'lat[itude]*[:\s]*(\d+\.?\d*)[,\s]*lon[gitude]*[:\s]*(\d+\.?\d*)',
                r'(\d+\.?\d*)[,\s]+(\d+\.?\d*)',
            ]
            
            for pattern in coord_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    try:
                        lat, lon = float(match[0]), float(match[1])
                        if 6 <= lat <= 37 and 68 <= lon <= 98:
                            logger.info(f"Search found coordinates for {place_name}: ({lat}, {lon})")
                            return lat, lon
                    except (ValueError, IndexError):
                        continue
    except Exception as e:
        logger.error(f"Error searching coordinates for {place_name}: {e}")
    
    # If all methods fail, return None to indicate failure
    logger.error(f"Could not find valid coordinates for {place_name}")
    return None, None

def get_place_images(place_name):
    """Fetch web images for a place using search API."""
    try:
        # Use Tavily search to find images
        image_query = f"{place_name} India tourist attractions landmarks photos images"
        search_results = search.invoke(image_query)
        
        images = []
        for result in search_results:
            # Extract image URLs from search results
            if 'images' in result:
                for img in result['images'][:3]:  # Limit to 3 images per result
                    images.append({
                        'url': img.get('url', ''),
                        'title': img.get('title', f'{place_name} Image'),
                        'source': result.get('url', '')
                    })
            
            # Also check for images in content
            content = result.get('content', '')
            if 'jpg' in content or 'jpeg' in content or 'png' in content:
                # Extract image URLs from content using regex
                img_urls = re.findall(r'https?://[^\s]+\.(?:jpg|jpeg|png|gif)', content)
                for url in img_urls[:2]:  # Limit to 2 images per content
                    images.append({
                        'url': url,
                        'title': f'{place_name} Image',
                        'source': result.get('url', '')
                    })
        
        # If no images found through search, use placeholder images
        if not images:
            images = [
                {
                    'url': f'/placeholder.svg?height=300&width=400&text={place_name.replace(" ", "+")}',
                    'title': f'{place_name} Placeholder',
                    'source': 'placeholder'
                }
            ]
        
        return images[:5]  # Return maximum 5 images
        
    except Exception as e:
        logger.error(f"Error fetching images for {place_name}: {e}")
        return [{
            'url': f'/placeholder.svg?height=300&width=400&text={place_name.replace(" ", "+")}',
            'title': f'{place_name} Placeholder',
            'source': 'placeholder'
        }]

def get_weather_data(lat, lon, start_date=None, days=7):
    """Fetch weather data for given coordinates and travel dates."""
    try:
        # Current weather
        current_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        response = requests.get(current_url, timeout=10)
        response.raise_for_status()
        weather_data = response.json()
        
        temp = weather_data["main"]["temp"]
        feels_like = weather_data["main"]["feels_like"]
        humidity = weather_data["main"]["humidity"]
        description = weather_data["weather"][0]["description"]
        wind_speed = weather_data["wind"]["speed"]
        
        # Get forecast for travel dates if start_date is provided
        forecast_data = []
        try:
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
            forecast_response = requests.get(forecast_url, timeout=10)
            forecast_response.raise_for_status()
            forecast_json = forecast_response.json()
            
            if "list" in forecast_json and start_date:
                # Calculate date range for travel period
                travel_dates = []
                for i in range(-7, days + 7):  # 7 days before to 7 days after travel
                    travel_date = start_date + datetime.timedelta(days=i)
                    travel_dates.append(travel_date.strftime("%d %b"))
                
                # Process forecast entries for travel period
                daily_forecasts = {}
                
                for entry in forecast_json["list"]:
                    entry_date = datetime.datetime.fromtimestamp(entry["dt"])
                    date_str = entry_date.strftime("%d %b")
                    
                    if date_str in travel_dates:
                        if date_str not in daily_forecasts:
                            daily_forecasts[date_str] = {
                                "temp_min": entry["main"]["temp_min"],
                                "temp_max": entry["main"]["temp_max"],
                                "conditions": [entry["weather"][0]["description"]],
                                "humidity": [entry["main"]["humidity"]],
                                "wind_speed": [entry["wind"]["speed"]]
                            }
                        else:
                            daily_forecasts[date_str]["temp_min"] = min(daily_forecasts[date_str]["temp_min"], entry["main"]["temp_min"])
                            daily_forecasts[date_str]["temp_max"] = max(daily_forecasts[date_str]["temp_max"], entry["main"]["temp_max"])
                            daily_forecasts[date_str]["conditions"].append(entry["weather"][0]["description"])
                            daily_forecasts[date_str]["humidity"].append(entry["main"]["humidity"])
                            daily_forecasts[date_str]["wind_speed"].append(entry["wind"]["speed"])
                
                # Convert to list and determine most common condition for each day
                for date, data in daily_forecasts.items():
                    # Find most common condition
                    condition_counts = {}
                    for condition in data["conditions"]:
                        condition_counts[condition] = condition_counts.get(condition, 0) + 1
                    most_common_condition = max(condition_counts.items(), key=lambda x: x[1])[0]
                    
                    # Calculate average humidity and wind speed
                    avg_humidity = sum(data["humidity"]) / len(data["humidity"])
                    avg_wind_speed = sum(data["wind_speed"]) / len(data["wind_speed"])
                    
                    forecast_data.append({
                        "date": date,
                        "temp_min": round(data["temp_min"]),
                        "temp_max": round(data["temp_max"]),
                        "condition": most_common_condition,
                        "humidity": round(avg_humidity),
                        "wind_speed": round(avg_wind_speed, 1)
                    })
                
                # Sort by date
                forecast_data.sort(key=lambda x: datetime.datetime.strptime(x["date"], "%d %b"))
            
        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            
        return {
            "current": f"Currently {temp}°C (feels like {feels_like}°C) with {description}, {humidity}% humidity, wind {wind_speed} m/s.",
            "forecast": forecast_data
        }
    except Exception as e:
        logger.error(f"Error fetching weather for ({lat}, {lon}): {e}")
        return {
            "current": "Weather data not available.",
            "forecast": []
        }

def get_additional_tourist_places(existing_places, region="India", count=3):
    """Get additional tourist places to fill extra days."""
    try:
        # Create a query to find more places in the same region
        existing_names = [p["name"] for p in existing_places]
        query = f"Popular tourist destinations in {region} India excluding {', '.join(existing_names[:3])}"
        
        search_results = search.invoke(query)
        
        prompt = ChatPromptTemplate.from_template("""
        Based on the search results, suggest {count} additional popular tourist destinations in India that are different from these existing places: {existing_places}.
        
        Provide a JSON array with each place having:
        - "name": the destination name
        - "latitude": approximate latitude
        - "longitude": approximate longitude
        - "reason": why this place is worth visiting
        
        Search Results: {search_results}
        """)
        
        chain = prompt | model | StrOutputParser()
        response = chain.invoke({
            "count": count,
            "existing_places": ", ".join(existing_names),
            "search_results": search_results
        })
        
        clean_response = clean_json(response)
        additional_places = json.loads(clean_response)
        
        # Convert to full place info format
        full_places = []
        for place_data in additional_places:
            place_info = get_place_info(place_data["name"])
            full_places.append({
                "name": place_data["name"],
                "latitude": place_info["latitude"],
                "longitude": place_info["longitude"],
                "top_attractions": place_info["top_attractions"],
                "hidden_gems": place_info["hidden_gems"],
                "local_culture": place_info["local_culture"],
                "traditional_clothing": place_info["traditional_clothing"],
                "cultural_experiences": place_info["cultural_experiences"],
                "shopping_spots": place_info["shopping_spots"],
                "local_tips": place_info["local_tips"],
                "restaurants": place_info["restaurants"],
                "hospitals": place_info["hospitals"],
                "transport": place_info["transport"],
                "yearly_weather": place_info["yearly_weather"],
                "current_weather": place_info["current_weather"],
                "forecast": place_info.get("forecast", []),
                "best_time_to_visit": place_info.get("best_time_to_visit", ""),
                "typical_costs": place_info.get("typical_costs", {}),
                "images": get_place_images(place_data["name"]),
                "is_additional": True,
                "reason_to_visit": place_data.get("reason", "Additional destination for your trip")
            })
        
        return full_places
        
    except Exception as e:
        logger.error(f"Error getting additional places: {e}")
        return []

def get_place_info(place):
    """Fetch comprehensive place information using Tavily search and Gemini with enhanced coordinate fetching."""
    try:
        # Enhanced query to ensure specific results for India
        query = f"Tourist attractions, hidden gems, local culture, traditional clothing, festivals, transport facilities, restaurants, hospitals, coordinates, yearly weather in {place}, India. Include specific latitude and longitude coordinates."
        search_results = search.invoke(query)
        logger.info(f"Search results for {place}: {search_results}")

        # Enhanced query for more detailed information including booking and shopping
        detailed_query = f"Detailed tourist information for {place}, India: specific attractions with names, exact restaurant names with addresses, hospital names and locations, shopping markets and malls, online booking platforms for hotels and activities, local handicrafts and souvenirs, cultural festivals with dates, traditional clothing styles, authentic local food dishes, hidden gems and secret spots, insider travel tips, transportation hubs and stations, emergency contacts and services"
        detailed_search_results = search.invoke(detailed_query)

        prompt = ChatPromptTemplate.from_template("""
        Based on the following search results, provide a JSON with keys:
        - "latitude" (float, default 0.0 if not found)
        - "longitude" (float, default 0.0 if not found)
        - "top_attractions" (list, at least 3 attractions, default ["No specific attractions found"])
        - "hidden_gems" (list, at least 3 lesser-known places or experiences, default ["No hidden gems found"])
        - "local_culture" (object with keys: "traditions", "festivals", "art_forms", "languages")
        - "traditional_clothing" (object with keys: "men", "women", "occasions", "where_to_buy")
        - "cultural_experiences" (list, unique cultural activities or experiences, default ["No specific cultural experiences found"])
        - "restaurants" (list, at least 3 restaurants, default ["No specific restaurants found"])
        - "hospitals" (list, at least 2 hospital, default ["No specific hospitals found"])
        - "transport" (string, transport facilities, default "No specific transport info available")
        - "yearly_weather" (string, weather overview, default "Weather data not available")
        - "typical_costs" (object with keys: "accommodation", "food", "transport", "attractions", all values in INR)
        - "best_time_to_visit" (string, when is the best time to visit this place)
        - "shopping_spots" (list, places to shop for local items, default ["No specific shopping spots found"])
        - "local_tips" (list, insider tips for travelers, default ["No specific tips available"])

        Ensure all keys are present and data is specific to {place}, India. Use default values if data is missing.
        
        Search Results:
        {search_results}
        """)

        chain = prompt | model | StrOutputParser()
        response = chain.invoke({"place": place, "search_results": search_results})
        clean_response = clean_json(response)
        place_info = json.loads(clean_response)

        # Use enhanced coordinate fetching
        lat, lon = get_enhanced_coordinates(place)
        if lat is not None and lon is not None:
            place_info["latitude"] = lat
            place_info["longitude"] = lon
        else:
            # If enhanced method fails, try to use coordinates from Gemini response
            if place_info.get("latitude", 0.0) == 0.0 or place_info.get("longitude", 0.0) == 0.0:
                raise ValueError(f"Could not find valid coordinates for {place}")

        # Fetch current weather and forecast
        if place_info["latitude"] != 0.0 and place_info["longitude"] != 0.0:
            weather_data = get_weather_data(place_info["latitude"], place_info["longitude"])
            place_info["current_weather"] = weather_data["current"]
            place_info["forecast"] = weather_data["forecast"]
            
            # We'll add distances later in a separate step
            place_info["distances"] = []
        else:
            place_info["current_weather"] = "Weather data not available"
            place_info["forecast"] = []

        # Set default values for new fields if not provided
        if "hidden_gems" not in place_info:
            place_info["hidden_gems"] = ["No hidden gems found"]
        if "local_culture" not in place_info:
            place_info["local_culture"] = {
                "traditions": "Local traditions information not available",
                "festivals": "Festival information not available", 
                "art_forms": "Art forms information not available",
                "languages": "Language information not available"
            }
        if "traditional_clothing" not in place_info:
            place_info["traditional_clothing"] = {
                "men": "Traditional men's clothing information not available",
                "women": "Traditional women's clothing information not available",
                "occasions": "Occasion-specific clothing information not available",
                "where_to_buy": "Local markets and shops"
            }
        if "cultural_experiences" not in place_info:
            place_info["cultural_experiences"] = ["No specific cultural experiences found"]
        if "shopping_spots" not in place_info:
            place_info["shopping_spots"] = ["No specific shopping spots found"]
        if "local_tips" not in place_info:
            place_info["local_tips"] = ["No specific tips available"]

        # Set default best time to visit if not provided
        if "best_time_to_visit" not in place_info or not place_info["best_time_to_visit"]:
            place_info["best_time_to_visit"] = "October to March is generally the best time to visit most parts of India when the weather is pleasant."

        return place_info
    except Exception as e:
        logger.error(f"Error fetching info for {place}: {e}")
        return {
            "latitude": 0.0,
            "longitude": 0.0,
            "top_attractions": ["No specific attractions found"],
            "hidden_gems": ["No hidden gems found"],
            "local_culture": {
                "traditions": "Local traditions information not available",
                "festivals": "Festival information not available", 
                "art_forms": "Art forms information not available",
                "languages": "Language information not available"
            },
            "traditional_clothing": {
                "men": "Traditional men's clothing information not available",
                "women": "Traditional women's clothing information not available",
                "occasions": "Occasion-specific clothing information not available",
                "where_to_buy": "Local markets and shops"
            },
            "cultural_experiences": ["No specific cultural experiences found"],
            "restaurants": ["No specific restaurants found"],
            "hospitals": ["No specific hospitals found"],
            "transport": "No specific transport info available",
            "yearly_weather": "Weather data not available",
            "current_weather": "Weather data not available",
            "forecast": [],
            "best_time_to_visit": "October to March is generally the best time to visit most parts of India when the weather is pleasant.",
            "shopping_spots": ["No specific shopping spots found"],
            "local_tips": ["No specific tips available"],
            "typical_costs": {
                "accommodation": "2000-5000 INR per night",
                "food": "500-1000 INR per day",
                "transport": "500-1000 INR per day",
                "attractions": "500-1000 INR per day"
            }
        }

def find_nearby_places(lat, lon, place_name, num_places=5):
    """Find nearby tourist places using Gemini."""
    try:
        prompt = ChatPromptTemplate.from_template("""
        What are {num_places} popular tourist attractions and destinations near {place_name}, India that are within 150km of coordinates {lat}, {lon}?
        Focus on well-known tourist destinations, heritage sites, viewpoints, hill stations, beaches, temples, forts, and popular attractions.
        Make sure each place is distinctly different and located in different areas/directions from the main location.
        
        Provide the response as a JSON array with each place having these properties:
        - "name": the name of the specific tourist attraction or destination
        - "distance_km": approximate distance in km from the main location
        - "description": a detailed description of what makes this place interesting for tourists
        - "attractions": an array of 2-3 specific things to see or activities to do at this place
        - "type": type of destination (e.g., "hill_station", "heritage_site", "beach", "temple", "fort", "wildlife")

        Example format:
        [
          {{
            "name": "Famous Temple Complex",
            "distance_km": 45,
            "description": "Ancient temple complex dating back to the 12th century with intricate carvings",
            "attractions": ["Main Shrine", "Museum Gallery", "Sculpture Garden"],
            "type": "heritage_site"
          }}
        ]
        """)
        
        chain = prompt | model | StrOutputParser()
        response = chain.invoke({"place_name": place_name, "lat": lat, "lon": lon, "num_places": num_places})
        clean_response = clean_json(response)
        nearby_places = json.loads(clean_response)
        
        # Ensure we have at least the requested number of places
        if not nearby_places or len(nearby_places) == 0:
            return [{
                "name": f"Day trip from {place_name}",
                "distance_km": 30,
                "description": f"Explore the popular tourist attractions near {place_name}",
                "attractions": ["Heritage Monuments", "Popular Viewpoints", "Local Markets"],
                "type": "day_trip"
            }]
            
        return nearby_places
    except Exception as e:
        logger.error(f"Error finding nearby places for {place_name}: {e}")
        return [{
            "name": f"Day trip from {place_name}",
            "distance_km": 30,
            "description": f"Explore the popular tourist attractions near {place_name}",
            "attractions": ["Heritage Monuments", "Popular Viewpoints", "Local Markets"],
            "type": "day_trip"
        }]

def compute_shortest_path(locations):
    """Compute shortest path using a simple TSP approximation."""
    client = Client(key=ORS_API_KEY)
    try:
        distance_matrix = client.distance_matrix(
            locations=locations,
            profile='driving-car',
            metrics=['distance', 'duration'],
            units='km'
        )
        distances = distance_matrix['distances']
        durations = distance_matrix['durations']
    except exceptions.ApiError as e:
        logger.error(f"Error computing distance matrix: {e}")
        return list(range(len(locations)), [], 0)

    # Handle None values in distance matrix
    for i in range(len(distances)):
        for j in range(len(distances[i])):
            if distances[i][j] is None:
                distances[i][j] = float('inf') if i != j else 0
            if durations[i][j] is None:
                durations[i][j] = float('inf') if i != j else 0

    # TSP approximation
    path = [0]
    visited = {0}
    current = 0
    total_distance = 0

    while len(visited) < len(locations):
        next_place = min(
            (i for i in range(len(locations)) if i not in visited),
            key=lambda i: distances[current][i]
        )
        total_distance += distances[current][next_place]
        path.append(next_place)
        visited.add(next_place)
        current = next_place

    # Compute routes
    routes = []
    route_points = []
    for i in range(len(path) - 1):
        start = locations[path[i]]
        end = locations[path[i + 1]]
        try:
            route = client.directions(
                coordinates=[start, end],
                profile='driving-car',
                format='geojson'
            )
            geojson_coords = route['features'][0]['geometry']['coordinates']
            route_coords = [[coord[1], coord[0]] for coord in geojson_coords]
            route_points.append(route_coords)
        except exceptions.ApiError:
            route_coords = [[start[1], start[0]], [end[1], end[0]]]
            route_points.append(route_coords)
        routes.append(route_coords)

    return path, routes, total_distance, route_points

def recommend_transport(distance_km, duration_hours, budget_per_person=5000):
    """Recommend transport options based on distance, duration, and budget."""
    if distance_km == 0 or duration_hours == 0:
        return {
            "mode": "Car", 
            "duration": "Unknown", 
            "cost": 0,
            "options": []
        }

    # Calculate costs based on distance and mode
    car_cost = max(300, int(distance_km * 15))  # Base 300 INR or 15 INR per km
    bus_cost = max(100, int(distance_km * 5))   # Base 100 INR or 5 INR per km
    train_cost = max(200, int(distance_km * 8)) # Base 200 INR or 8 INR per km
    flight_cost = max(2500, int(distance_km * 12)) # Base 2500 INR or 12 INR per km

    # Create transport options
    options = []

    # Car option
    car_option = {
        "mode": "Car",
        "duration": f"{duration_hours:.1f} hours",
        "cost": car_cost,
        "budget_friendly": car_cost <= budget_per_person * 0.2
    }
    options.append(car_option)

    # Bus option (if applicable)
    if distance_km > 10:
        bus_duration = duration_hours * 2
        bus_option = {
            "mode": "Bus",
            "duration": f"{bus_duration:.1f} hours",
            "cost": bus_cost,
            "budget_friendly": bus_cost <= budget_per_person * 0.2
        }
        options.append(bus_option)

    # Train option (if applicable)
    if distance_km > 50:
        train_duration = duration_hours * 1.5
        train_option = {
            "mode": "Train",
            "duration": f"{train_duration:.1f} hours",
            "cost": train_cost,
            "budget_friendly": train_cost <= budget_per_person * 0.2
        }
        options.append(train_option)

    # Flight option (if applicable)
    if distance_km > 300:
        flight_duration = 1.0 + (distance_km / 800)
        flight_option = {
            "mode": "Flight",
            "duration": f"{flight_duration:.1f} hours",
            "cost": flight_cost,
            "budget_friendly": flight_cost <= budget_per_person * 0.2
        }
        options.append(flight_option)

    # Determine recommended option based on budget and distance
    recommended = None

    if budget_per_person < 2000:  # Low budget
        # Sort by cost for low budget
        options.sort(key=lambda x: x["cost"])
        recommended = options[0]
    elif budget_per_person > 10000 and distance_km > 500:  # High budget, long distance
        # Prefer flight for high budget and long distance
        flight_options = [opt for opt in options if opt["mode"] == "Flight"]
        if flight_options:
            recommended = flight_options[0]
        else:
            # Sort by duration if no flight available
            options.sort(key=lambda x: float(x["duration"].split()[0]))
            recommended = options[0]
    elif distance_km > 300:  # Medium-long distance
        # Prefer train for medium-long distance
        train_options = [opt for opt in options if opt["mode"] == "Train"]
        if train_options:
            recommended = train_options[0]
        else:
            # Sort by balance of cost and duration
            options.sort(key=lambda x: (float(x["duration"].split()[0]) * 0.6) + (x["cost"] / budget_per_person * 0.4))
            recommended = options[0]
    else:  # Short distance
        # For short distances, prefer car or bus based on budget
        if budget_per_person > 5000:
            car_options = [opt for opt in options if opt["mode"] == "Car"]
            if car_options:
                recommended = car_options[0]
        else:
            bus_options = [opt for opt in options if opt["mode"] == "Bus"]
            if bus_options:
                recommended = bus_options[0]
            else:
                car_options = [opt for opt in options if opt["mode"] == "Car"]
                if car_options:
                    recommended = car_options[0]

    # If still no recommendation, use the first option
    if not recommended and options:
        recommended = options[0]
    elif not recommended:
        recommended = car_option  # Default to car if no options

    # Mark the recommended option
    for option in options:
        if option["mode"] == recommended["mode"]:
            option["recommended"] = True
        else:
            option["recommended"] = False

    return {
        "mode": recommended["mode"],
        "duration": recommended["duration"],
        "cost": recommended["cost"],
        "options": options
    }

def create_daily_plan(places, transport_info, total_days, start_date=None, budget_per_person=5000):
    """Generate a detailed day-to-day itinerary ensuring different places for different days."""
    num_places = len(places)
    daily_plan = []

    # If we have fewer places than days, find additional nearby places
    if num_places < total_days:
        logger.info(f"Need to find additional places: {total_days} days but only {num_places} places")
        
        # Find nearby places for each main destination
        additional_places = []
        for main_place in places:
            nearby_places = find_nearby_places(
                main_place["latitude"], 
                main_place["longitude"], 
                main_place["name"], 
                num_places=3
            )
            
            for nearby in nearby_places:
                # Create a new place entry for nearby attraction
                new_place = {
                    "name": nearby["name"],
                    "latitude": main_place["latitude"],  # Use main place coordinates as approximation
                    "longitude": main_place["longitude"],
                    "top_attractions": nearby["attractions"],
                    "hidden_gems": [f"Hidden spots around {nearby['name']}"],
                    "local_culture": main_place["local_culture"],  # Inherit from main place
                    "traditional_clothing": main_place["traditional_clothing"],
                    "cultural_experiences": [f"Cultural experiences in {nearby['name']}"],
                    "shopping_spots": main_place["shopping_spots"],
                    "local_tips": [f"Visit {nearby['name']} early morning for best experience"],
                    "restaurants": main_place["restaurants"],  # Reuse from main place
                    "hospitals": main_place["hospitals"],      # Reuse from main place
                    "transport": main_place["transport"],      # Reuse from main place
                    "yearly_weather": main_place["yearly_weather"],
                    "current_weather": main_place["current_weather"],
                    "forecast": main_place["forecast"],
                    "best_time_to_visit": main_place["best_time_to_visit"],
                    "typical_costs": main_place["typical_costs"],
                    "booking_links": main_place.get("booking_links", {}),
                    "shopping_links": main_place.get("shopping_links", {}),
                    "distances": [],
                    "is_nearby_attraction": True,
                    "main_destination": main_place["name"],
                    "distance_from_main": nearby["distance_km"],
                    "description": nearby["description"],
                    "attraction_type": nearby.get("type", "attraction"),
                    "images": get_place_images(nearby["name"])
                }
                additional_places.append(new_place)
        
        # Add additional places to the main places list
        places.extend(additional_places[:total_days - num_places])
        logger.info(f"Added {len(additional_places[:total_days - num_places])} additional places")

    # Now create day-to-day distribution ensuring no repetition
    day_to_places_map = {}
    used_places = set()

    # Distribute places across days ensuring each day gets different places
    for day in range(total_days):
        day_places = []
        
        # Find unused places for this day
        available_places = [i for i in range(len(places)) if i not in used_places]
        
        if available_places:
            # For each day, assign 1-2 places maximum to avoid overcrowding
            places_for_day = min(2, len(available_places))
            
            # If it's the last few days and we still have many places, assign more
            remaining_days = total_days - day
            remaining_places = len(available_places)
            if remaining_days <= 3 and remaining_places > remaining_days:
                places_for_day = min(3, math.ceil(remaining_places / remaining_days))
            
            # Select places for this day
            selected_places = available_places[:places_for_day]
            day_places.extend(selected_places)
            used_places.update(selected_places)
        
        day_to_places_map[day] = day_places

    # Generate dates if start_date is provided
    dates = []
    if start_date:
        for i in range(total_days):
            current_date = start_date + datetime.timedelta(days=i)
            dates.append(current_date.strftime("%d %b %Y"))
    else:
        dates = [""] * total_days

    # Create daily plan based on the distribution
    for day in range(total_days):
        day_place_indices = day_to_places_map.get(day, [])
        if not day_place_indices:
            continue
            
        day_places = [places[idx] for idx in day_place_indices]
        
        itinerary_items = []
        start_time = 8
        
        # Morning activities for first place
        first_place = day_places[0]
        is_nearby_attraction = first_place.get("is_nearby_attraction", False)
        
        if is_nearby_attraction:
            # Nearby attraction itinerary
            adjusted_time = start_time
            am_pm = "AM" if adjusted_time < 12 else "PM"
            display_time = adjusted_time if adjusted_time <= 12 else adjusted_time - 12
            itinerary_items.append({
                "time": f"{display_time}:00 {am_pm} IST",
                "content": f"Visit {first_place['name']} ({first_place['distance_from_main']} km from {first_place['main_destination']})"
            })
            start_time += 1
            
            adjusted_time = start_time
            am_pm = "AM" if adjusted_time < 12 else "PM"
            display_time = adjusted_time if adjusted_time <= 12 else adjusted_time - 12
            itinerary_items.append({
                "time": f"{display_time}:00 {am_pm} IST",
                "content": f"{first_place['description']}"
            })
            start_time += 2
        else:
            # Regular place itinerary
            attractions = first_place['top_attractions'][:2] if first_place['top_attractions'][0] != "No specific attractions found" else ["local attractions"]
            adjusted_time = start_time
            am_pm = "AM" if adjusted_time < 12 else "PM"
            display_time = adjusted_time if adjusted_time <= 12 else adjusted_time - 12
            itinerary_items.append({
                "time": f"{display_time}:00 {am_pm} IST",
                "content": f"Explore {first_place['name']} - Visit {', '.join(attractions)}"
            })
            start_time += 2
        
        # Add lunch
        restaurant = first_place['restaurants'][0] if first_place['restaurants'][0] != "No specific restaurants found" else "local restaurant"
        adjusted_time = start_time
        am_pm = "AM" if adjusted_time < 12 else "PM"
        display_time = adjusted_time if adjusted_time <= 12 else adjusted_time - 12
        itinerary_items.append({
            "time": f"{display_time}:00 {am_pm} IST",
            "content": f"Lunch at {restaurant}"
        })
        start_time += 1
        
        # Afternoon activities
        if len(day_places) > 1:
            # Visit second place
            second_place = day_places[1]
            attractions = second_place['top_attractions'][:2] if second_place['top_attractions'][0] != "No specific attractions found" else ["local attractions"]
            adjusted_time = start_time
            am_pm = "AM" if adjusted_time < 12 else "PM"
            display_time = adjusted_time if adjusted_time <= 12 else adjusted_time - 12
            itinerary_items.append({
                "time": f"{display_time}:00 {am_pm} IST",
                "content": f"Explore {second_place['name']} - Visit {', '.join(attractions)}"
            })
            start_time += 2
        else:
            # Continue with first place if only one place for the day
            if len(first_place['top_attractions']) > 2 and first_place['top_attractions'][0] != "No specific attractions found":
                more_attractions = first_place['top_attractions'][2:4]
                adjusted_time = start_time
                am_pm = "AM" if adjusted_time < 12 else "PM"
                display_time = adjusted_time if adjusted_time <= 12 else adjusted_time - 12
                itinerary_items.append({
                    "time": f"{display_time}:00 {am_pm} IST",
                    "content": f"Continue exploring {first_place['name']} - Visit {', '.join(more_attractions)}"
                })
                start_time += 2
        
        # Evening activities
        last_place = day_places[-1]
        restaurant = last_place['restaurants'][1] if len(last_place['restaurants']) > 1 and last_place['restaurants'][0] != "No specific restaurants found" else "local restaurants"
        adjusted_time = start_time
        am_pm = "AM" if adjusted_time < 12 else "PM"
        display_time = adjusted_time if adjusted_time <= 12 else adjusted_time - 12
        itinerary_items.append({
            "time": f"{display_time}:00 {am_pm} IST",
            "content": f"Evening leisure in {last_place['name']} - Dine at {restaurant}"
        })
        
        daily_plan.append({
            "day": f"Day {day + 1}",
            "date": dates[day],
            "places": [p["name"] for p in day_places],
            "itinerary_items": itinerary_items
        })

    return daily_plan

def calculate_budget_breakdown(budget, days, members, places):
    """Calculate budget breakdown based on trip details."""
    budget_per_person = budget / members
    budget_per_day = budget / days

    # Estimate typical costs based on place information
    accommodation_cost = 0
    food_cost = 0
    transport_cost = 0
    attractions_cost = 0

    for place in places:
        if 'typical_costs' in place:
            # Extract numeric values from cost strings
            try:
                # Parse accommodation cost (per night)
                acc_cost = place['typical_costs']['accommodation']
                if isinstance(acc_cost, str):
                    acc_cost = int(re.search(r'(\d+)', acc_cost.split('-')[0]).group(1))
                accommodation_cost += acc_cost
                
                # Parse attractions cost (per day)
                attr_cost_str = place['typical_costs']['attractions']
                if isinstance(attr_cost_str, str):
                    attr_cost_val = int(re.search(r'(\d+)', attr_cost_str.split('-')[0]).group(1))
                    attractions_cost += attr_cost_val
            except (AttributeError, ValueError, TypeError):
                # Default values if parsing fails
                accommodation_cost += 3000  # Default: 3000 INR per night
                attractions_cost += 500  # Default: 500 INR per day

    # Adjust costs based on number of days and members
    accommodation_cost = (accommodation_cost / len(places)) * days  # Average per place * days
    food_cost = 800 * days * members  # 800 INR per day per person (removed local cuisine focus)
    attractions_cost = (attractions_cost / len(places)) * days * members  # Average per place * days * members

    # Transport cost estimation (15-25% of total budget)
    transport_cost = budget * 0.2  # 20% of total budget for transport

    # Miscellaneous expenses (10% of total budget)
    misc_cost = budget * 0.1

    # Create budget breakdown
    budget_breakdown = [
        {"category": "Accommodation", "amount": int(accommodation_cost)},
        {"category": "Food & Dining", "amount": int(food_cost)},
        {"category": "Transportation", "amount": int(transport_cost)},
        {"category": "Attractions & Activities", "amount": int(attractions_cost)},
        {"category": "Miscellaneous", "amount": int(misc_cost)}
    ]

    total_estimated_expenses = sum(item["amount"] for item in budget_breakdown)
    remaining_budget = budget - total_estimated_expenses

    # Budget tips based on analysis
    budget_tips = [
        "Book accommodation in advance to get better rates",
        "Use public transportation where available to save on transport costs",
        "Consider group discounts for attractions when traveling with family/friends",
        "Try local restaurants and street food for authentic experiences at lower costs",
        "Keep a buffer of 10-15% for unexpected expenses"
    ]

    if remaining_budget < 0:
        budget_tips.insert(0, "Your estimated expenses exceed your budget. Consider extending your budget or reducing the number of places/days.")

    return {
        "budget_per_person": int(budget_per_person),
        "budget_per_day": int(budget_per_day),
        "budget_breakdown": budget_breakdown,
        "total_estimated_expenses": total_estimated_expenses,
        "remaining_budget": remaining_budget,
        "budget_tips": budget_tips
    }

def get_booking_shopping_links(place_name, place_info):
    """Generate booking and shopping links for a place using Gemini."""
    try:
        prompt = ChatPromptTemplate.from_template("""
        For {place_name}, India, provide booking and shopping information in JSON format:
        {{
            "booking_links": {{
                "hotels": ["Hotel booking platform 1", "Hotel booking platform 2"],
                "activities": ["Activity booking platform 1", "Activity booking platform 2"],
                "transport": ["Transport booking platform 1", "Transport booking platform 2"]
            }},
            "shopping_spots": {{
                "local_markets": ["Market name 1 - specialty", "Market name 2 - specialty"],
                "malls": ["Mall name 1", "Mall name 2"],
                "handicrafts": ["Handicraft shop 1", "Handicraft shop 2"],
                "online_shopping": ["Online platform 1", "Online platform 2"]
            }}
        }}
        
        Focus on real, specific names of markets, malls, and booking platforms available in {place_name}.
        """)
        
        chain = prompt | model | StrOutputParser()
        response = chain.invoke({"place_name": place_name})
        clean_response = clean_json(response)
        booking_shopping = json.loads(clean_response)
        
        return booking_shopping
    except Exception as e:
        logger.error(f"Error getting booking/shopping links for {place_name}: {e}")
        return {
            "booking_links": {
                "hotels": ["MakeMyTrip", "Booking.com"],
                "activities": ["GetYourGuide", "Viator"],
                "transport": ["RedBus", "IRCTC"]
            },
            "shopping_spots": {
                "local_markets": ["Local markets available"],
                "malls": ["Shopping centers available"],
                "handicrafts": ["Local handicraft shops"],
                "online_shopping": ["Amazon India", "Flipkart"]
            }
        }

def parse_trip_description(description):
    """Parse natural language trip description using Gemini to extract trip details."""
    try:
        prompt = ChatPromptTemplate.from_template("""
        Extract travel information from this description: "{description}"
        
        Return a JSON with these exact keys:
        - "start_date": start date in YYYY-MM-DD format (if mentioned, otherwise null)
        - "end_date": end date in YYYY-MM-DD format (if mentioned, otherwise null) 
        - "days": number of days (calculate from dates or extract from text, default 7 if unclear)
        - "members": number of people/travelers (default 2 if unclear)
        - "budget": budget amount in INR (extract number only, default 50000 if unclear)
        - "places": array of destination names mentioned (at least 1 place required)
        - "preferences": any special preferences or requirements mentioned
        
        Examples:
        - "We want to visit Delhi and Agra for 5 days with 4 people and budget of 80000 rupees"
        - "Planning a trip to Rajasthan from March 15 to March 22 for 2 people with 60000 budget"
        - "Family vacation to Kerala and Goa, 3 adults, one week, around 1 lakh budget"
        
        If dates are mentioned, calculate days automatically. If only duration is mentioned, set start_date as 7 days from today.
        Always ensure places array has at least one valid Indian destination.
        """)
        
        chain = prompt | model | StrOutputParser()
        response = chain.invoke({"description": description})
        clean_response = clean_json(response)
        parsed_data = json.loads(clean_response)
        
        # Validate and set defaults
        if not parsed_data.get("places") or len(parsed_data["places"]) == 0:
            parsed_data["places"] = ["Delhi"]  # Default destination
            
        if not parsed_data.get("days") or parsed_data["days"] <= 0:
            parsed_data["days"] = 7
            
        if not parsed_data.get("members") or parsed_data["members"] <= 0:
            parsed_data["members"] = 2
            
        if not parsed_data.get("budget") or parsed_data["budget"] <= 0:
            parsed_data["budget"] = 50000
            
        # Handle dates
        if not parsed_data.get("start_date") and not parsed_data.get("end_date"):
            # Set start date as 7 days from today if no dates mentioned
            start_date = datetime.datetime.now() + datetime.timedelta(days=7)
            end_date = start_date + datetime.timedelta(days=parsed_data["days"] - 1)
            parsed_data["start_date"] = start_date.strftime("%Y-%m-%d")
            parsed_data["end_date"] = end_date.strftime("%Y-%m-%d")
        elif parsed_data.get("start_date") and not parsed_data.get("end_date"):
            # Calculate end date from start date and days
            start_date = datetime.datetime.strptime(parsed_data["start_date"], "%Y-%m-%d")
            end_date = start_date + datetime.timedelta(days=parsed_data["days"] - 1)
            parsed_data["end_date"] = end_date.strftime("%Y-%m-%d")
        elif parsed_data.get("end_date") and not parsed_data.get("start_date"):
            # Calculate start date from end date and days
            end_date = datetime.datetime.strptime(parsed_data["end_date"], "%Y-%m-%d")
            start_date = end_date - datetime.timedelta(days=parsed_data["days"] - 1)
            parsed_data["start_date"] = start_date.strftime("%Y-%m-%d")
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing trip description: {e}")
        # Return default values if parsing fails
        start_date = datetime.datetime.now() + datetime.timedelta(days=7)
        end_date = start_date + datetime.timedelta(days=6)
        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "days": 7,
            "members": 2,
            "budget": 50000,
            "places": ["Delhi"],
            "preferences": ""
        }

def has_meaningful_content(data, field_name):
    """Check if the data contains meaningful content and not default placeholder values."""
    if not data:
        return False
        
    # Check for common placeholder patterns
    placeholder_patterns = [
        "no specific",
        "not available",
        "information not available",
        "not found",
        "no hidden gems found",
        "no specific attractions found",
        "no specific restaurants found",
        "no specific hospitals found",
        "no specific shopping spots found",
        "no specific tips available",
        "no specific cultural experiences found"
    ]

    if isinstance(data, str):
        data_lower = data.lower()
        return not any(pattern in data_lower for pattern in placeholder_patterns)
    elif isinstance(data, list):
        if len(data) == 0:
            return False
        # Check if all items in list are placeholder content
        meaningful_items = []
        for item in data:
            if isinstance(item, str):
                item_lower = item.lower()
                if not any(pattern in item_lower for pattern in placeholder_patterns):
                    meaningful_items.append(item)
        return len(meaningful_items) > 0
    elif isinstance(data, dict):
        # For dictionaries, check if any value has meaningful content
        for key, value in data.items():
            if has_meaningful_content(value, key):
                return True
        return False

    return True

def is_tourism_or_weather_related(message):
    """Check if the message is related to tourism or weather."""
    tourism_keywords = [
        'travel', 'trip', 'destination', 'tourist', 'tourism', 'visit', 'vacation', 'holiday',
        'hotel', 'restaurant', 'attraction', 'sightseeing', 'culture', 'heritage', 'temple',
        'beach', 'mountain', 'hill station', 'palace', 'fort', 'museum', 'park', 'wildlife',
        'safari', 'trekking', 'adventure', 'pilgrimage', 'festival', 'food', 'cuisine',
        'shopping', 'market', 'handicraft', 'souvenir', 'guide', 'itinerary', 'package',
        'booking', 'accommodation', 'transport', 'flight', 'train', 'bus', 'taxi', 'cab',
        'india', 'delhi', 'mumbai', 'kolkata', 'chennai', 'bangalore', 'hyderabad', 'pune',
        'jaipur', 'agra', 'goa', 'kerala', 'rajasthan', 'kashmir', 'himachal', 'uttarakhand',
        'taj mahal', 'red fort', 'gateway of india', 'backwaters', 'golden temple',
        'places to visit', 'things to do', 'best time to visit', 'how to reach', 'landmark',
        'monument', 'architecture', 'historical', 'scenic', 'beautiful', 'famous', 'popular',
        'capital', 'state capital', 'traditions', 'customs', 'local culture', 'heritage',
        'traditional', 'folk', 'ethnic', 'cultural', 'history', 'historical significance'
    ]

    weather_keywords = [
        'weather', 'temperature', 'climate', 'rain', 'rainfall', 'monsoon', 'sunny', 'cloudy',
        'hot', 'cold', 'humid', 'dry', 'season', 'winter', 'summer', 'spring', 'autumn',
        'forecast', 'precipitation', 'humidity', 'wind', 'storm', 'cyclone', 'heat wave',
        'best weather', 'climate conditions', 'seasonal', 'meteorology'
    ]

    message_lower = message.lower()

    # Check for tourism keywords
    for keyword in tourism_keywords:
        if keyword in message_lower:
            return True

    # Check for weather keywords
    for keyword in weather_keywords:
        if keyword in message_lower:
            return True

    # Check for navigation requests
    for route in ROUTES:
        if (f"take me to {route['name']}" in message_lower or 
            f"open {route['name']}" in message_lower or
            message_lower == route['name']):
            return True

    return False

def is_likely_tourism_image(image_path):
    """Use AI to determine if an image is likely tourism-related."""
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17")
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()
        
        classification_prompt = """
        Analyze this image and determine if it shows any of the following tourism-related content:
        - Landmarks, monuments, or historical sites
        - Tourist attractions or destinations
        - Hotels, restaurants, or accommodation
        - Natural scenery like beaches, mountains, or landscapes
        - Cultural sites, temples, or religious places
        - Transportation hubs like airports, train stations
        - Tourist activities or experiences
        - Architecture or buildings of tourist interest
        - Markets, shopping areas, or local culture
        - Weather conditions at travel destinations
        
        Respond with only "YES" if the image shows tourism-related content, or "NO" if it doesn't.
        """
        
        response = model.generate_content([
            classification_prompt,
            {"mime_type": f"image/{Path(image_path).suffix[1:]}", "data": image_data}
        ])
        
        result = response.text.strip().upper()
        return result == "YES"
        
    except Exception as e:
        logger.error(f"Error classifying image: {e}")
        # If we can't classify, assume it might be tourism-related to avoid false negatives
        return True

def create_tourism_image_prompt(user_message):
    """Create a comprehensive prompt for analyzing tourism-related images."""
    return f"""
    You are a specialized travel assistant for India. The user has uploaded an image and asked: "{user_message}"

    Please analyze this image and provide comprehensive tourism information including:

    **LANDMARK/DESTINATION IDENTIFICATION:**
    - What landmark, monument, or destination is shown?
    - Where is this located (city, state, country)?
    - Historical significance and background
    - If it's a state capital or important administrative center

    **CULTURAL & TRADITIONAL INFORMATION:**
    - Local traditions and customs associated with this place
    - Traditional festivals celebrated here
    - Cultural significance and heritage value
    - Traditional clothing and attire of the region
    - Local art forms, music, and dance traditions
    - Historical importance and cultural legacy

    **TRAVEL INFORMATION:**
    - Best time to visit this place
    - How to reach this destination (nearest airport, railway station, bus stops)
    - Entry fees and visiting hours (if applicable)
    - Recommended duration for visit

    **NEARBY ATTRACTIONS:**
    - Other tourist attractions within 50km
    - Popular activities and experiences in the area
    - Cultural sites and heritage locations nearby

    **PRACTICAL TRAVEL TIPS:**
    - Best photography spots and timing
    - Local customs and etiquette to follow
    - What to wear and bring
    - Safety tips for visitors

    **ACCOMMODATION & DINING:**
    - Recommended hotels and guesthouses nearby
    - Popular local restaurants and food specialties
    - Traditional cuisine and must-try dishes
    - Budget ranges for different types of accommodation

    **WEATHER & SEASONAL INFO:**
    - Current weather conditions in the area
    - Seasonal variations and what to expect
    - Monsoon patterns and best weather months

    **CULTURAL CONTEXT:**
    - Cultural significance and local traditions
    - Festivals and events celebrated here
    - Local handicrafts and souvenirs available
    - Traditional markets and shopping areas

    **BOOKING & PLANNING:**
    - How to book tickets or tours
    - Recommended tour operators or guides
    - Package deals and group discounts available

    Provide detailed, accurate, and helpful information that would assist a traveler planning to visit this destination, with special emphasis on cultural traditions and historical significance.
    """

def create_restricted_prompt(user_message, is_image=False):
    """Create a prompt that restricts responses to tourism and weather topics."""
    if is_image:
        return create_tourism_image_prompt(user_message)
    else:
        return f"""
        You are a specialized travel assistant for India that ONLY provides information about:
        1. Tourism and travel-related topics (destinations, attractions, hotels, restaurants, culture, festivals, transportation, accommodation, etc.)
        2. Weather and climate information for travel planning
        3. Navigation help for travel websites
        4. Cultural traditions, customs, and heritage information
        5. State capitals and administrative information related to travel

        User question: "{user_message}"

        IMPORTANT RESTRICTIONS:
        - If the question is NOT related to tourism or weather, respond with: "I can only help with tourism and weather-related questions. Please ask me about Indian destinations, travel planning, attractions, or weather information."
        - Only provide information about travel, tourism, destinations, weather, cultural traditions, and related topics
        - Do not answer questions about other subjects like technology, politics, health, education, etc. unless they are directly related to travel

        If the question is tourism/weather related, provide helpful and detailed information about:
        - Indian travel destinations, attractions, weather conditions, travel tips, and planning advice
        - Cultural traditions, customs, festivals, and heritage information
        - State capitals and their significance for travelers
        - Traditional clothing, food, art forms, and local customs
        - Historical significance and cultural importance of places
        - Local festivals, celebrations, and cultural events
        - Traditional markets, handicrafts, and cultural shopping experiences

        Always include cultural and traditional information when discussing any Indian destination or state.
        """

# --- Voice Input Handler ---
@csrf_exempt
def process_voice_input(request):
    """Process voice input for trip planning."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            voice_text = data.get('voice_text', '')
            
            # Parse voice input for trip planning parameters
            # Expected format: "Plan a trip to Delhi, Mumbai for 5 days with 2 members and budget 50000"
            
            # Use Gemini to extract trip parameters from voice input
            prompt = ChatPromptTemplate.from_template("""
            Extract trip planning parameters from this voice input: "{voice_text}"
            
            Return a JSON with these keys:
            - "places": array of place names mentioned
            - "days": number of days (if mentioned)
            - "members": number of people (if mentioned)
            - "budget": budget amount in INR (if mentioned)
            - "success": true if parameters found, false otherwise
            - "message": explanation of what was extracted or what's missing
            
            If the input doesn't seem to be about trip planning, set success to false.
            """)
            
            chain = prompt | model | StrOutputParser()
            response = chain.invoke({"voice_text": voice_text})
            clean_response = clean_json(response)
            extracted_params = json.loads(clean_response)
            
            return JsonResponse(extracted_params)
            
        except Exception as e:
            logger.error(f"Error processing voice input: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Error processing voice input: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

# --- Enhanced Trip Description Processing ---
@csrf_exempt
def process_trip_description(request):
    """Process detailed trip description for comprehensive itinerary planning."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            description = data.get('description', '')
            
            # Use Gemini to extract comprehensive trip details
            prompt = ChatPromptTemplate.from_template("""
            You are an expert travel planner. Analyze this detailed trip description and extract comprehensive travel information: "{description}"
            
            Return a JSON with these exact keys:
            - "start_date": start date in YYYY-MM-DD format (if mentioned, otherwise calculate 7 days from today)
            - "end_date": end date in YYYY-MM-DD format (if mentioned, otherwise calculate based on days)
            - "days": number of days (calculate from dates or extract from text, minimum 1, maximum 30)
            - "members": number of people/travelers (extract from text, default 2 if unclear)
            - "budget": budget amount in INR (extract number only, default 50000 if unclear)
            - "places": array of destination names mentioned (at least 1 place required, all should be in India)
            - "preferences": any special preferences, interests, or requirements mentioned
            - "travel_style": type of travel (adventure, leisure, cultural, religious, family, etc.)
            - "accommodation_preference": preferred accommodation type (budget, mid-range, luxury, etc.)
            - "transport_preference": preferred transport mode (flight, train, car, bus, etc.)
            - "activities": specific activities or experiences mentioned
            - "dietary_requirements": any dietary restrictions or preferences mentioned
            - "accessibility_needs": any accessibility requirements mentioned
            - "success": true if extraction was successful, false otherwise
            - "message": explanation of what was extracted or any issues
            
            Examples of input:
            - "We want a cultural tour of Rajasthan for 10 days, 4 people, budget 2 lakhs, interested in palaces and forts"
            - "Planning a spiritual journey to Varanasi and Rishikesh, 5 days, solo travel, budget 30000, vegetarian food"
            - "Family vacation to Kerala backwaters and hill stations, 7 days, 2 adults 2 children, luxury resorts, 1.5 lakh budget"
            
            Always ensure:
            - Places array contains only valid Indian destinations
            - Budget is in INR (convert if mentioned in lakhs: 1 lakh = 100000)
            - Days is reasonable (1-30)
            - All extracted information is relevant to travel planning
            """)
            
            chain = prompt | model | StrOutputParser()
            response = chain.invoke({"description": description})
            clean_response = clean_json(response)
            extracted_data = json.loads(clean_response)
            
            # Validate and set defaults
            if not extracted_data.get("places") or len(extracted_data["places"]) == 0:
                extracted_data["places"] = ["Delhi"]
                
            if not extracted_data.get("days") or extracted_data["days"] <= 0:
                extracted_data["days"] = 7
            elif extracted_data["days"] > 30:
                extracted_data["days"] = 30
                
            if not extracted_data.get("members") or extracted_data["members"] <= 0:
                extracted_data["members"] = 2
                
            if not extracted_data.get("budget") or extracted_data["budget"] <= 0:
                extracted_data["budget"] = 50000
            
            # Handle dates
            if not extracted_data.get("start_date"):
                start_date = datetime.datetime.now() + datetime.timedelta(days=7)
                extracted_data["start_date"] = start_date.strftime("%Y-%m-%d")
                
            if not extracted_data.get("end_date"):
                start_date = datetime.datetime.strptime(extracted_data["start_date"], "%Y-%m-%d")
                end_date = start_date + datetime.timedelta(days=extracted_data["days"] - 1)
                extracted_data["end_date"] = end_date.strftime("%Y-%m-%d")
            
            extracted_data["success"] = True
            return JsonResponse(extracted_data)
            
        except Exception as e:
            logger.error(f"Error processing trip description: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Error processing trip description: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

# --- Main View Function ---

def AI_trip(request):
    """Handle AI-powered trip planning."""
    if request.method == "POST":
        # Check if this is a natural language description or form data
        trip_description = request.POST.get("trip_description")
        
        if trip_description:
            # Parse natural language description
            try:
                parsed_data = parse_trip_description(trip_description)
                
                # Use parsed data to set form values
                date_range = f"{parsed_data['start_date']} to {parsed_data['end_date']}"
                members = parsed_data["members"]
                budget = parsed_data["budget"]
                places_input = ", ".join(parsed_data["places"])
                days = parsed_data["days"]
                start_date = datetime.datetime.strptime(parsed_data["start_date"], "%Y-%m-%d")
                end_date = datetime.datetime.strptime(parsed_data["end_date"], "%Y-%m-%d")
                
            except Exception as e:
                return render(request, "AI_trip.html", {"error": f"Could not parse your trip description: {str(e)}"})
        else:
            # Handle regular form submission
            date_range = request.POST.get("date_range")
            members = request.POST.get("members")
            budget = request.POST.get("budget")
            places_input = request.POST.get("places")

            if not (members and places_input and budget):
                return render(request, "AI_trip.html", {"error": "Please fill all fields."})

            try:
                # Parse date range if provided
                days = 0
                start_date = None
                end_date = None
                
                if date_range:
                    date_parts = date_range.split(" to ")
                    if len(date_parts) == 2:
                        start_date = datetime.datetime.strptime(date_parts[0], "%Y-%m-%d")
                        end_date = datetime.datetime.strptime(date_parts[1], "%Y-%m-%d")
                        days = (end_date - start_date).days + 1
                    else:
                        return render(request, "AI_trip.html", {"error": "Invalid date range format."})
                else:
                    return render(request, "AI_trip.html", {"error": "Please select travel dates."})
                
                members = int(members)
                budget = int(budget)
                
                if days <= 0:
                    return render(request, "AI_trip.html", {"error": "Please select valid travel dates."})
                    
            except ValueError:
                return render(request, "AI_trip.html", {"error": "Invalid input. Please check your entries."})

        # Continue with existing trip planning logic...
        places_list = [place.strip() for place in places_input.split(",") if place.strip()]
        
        # Adjust specific landmarks to cities
        adjusted_places = []
        for place in places_list:
            if place.lower() == "hawa mahal":
                adjusted_places.append("Jaipur")
            elif place.lower() == "taj mahal":
                adjusted_places.append("Agra")
            elif place.lower() == "gateway of india":
                adjusted_places.append("Mumbai")
            else:
                adjusted_places.append(place)

        try:
            # Fetch place information with enhanced coordinate fetching
            all_places_info = []
            locations = []
            failed_places = []
            
            for place in adjusted_places:
                place_info = get_place_info(place)
                # Get booking and shopping links
                booking_shopping = get_booking_shopping_links(place, place_info)
                place_info["booking_links"] = booking_shopping["booking_links"]
                place_info["shopping_links"] = booking_shopping["shopping_spots"]
                # Get images for the place
                place_images = get_place_images(place)
                
                if place_info["latitude"] == 0.0 or place_info["longitude"] == 0.0:
                    failed_places.append(place)
                    logger.warning(f"Could not find coordinates for {place}, skipping...")
                    continue
                    
                all_places_info.append({
                    "name": place,
                    "latitude": place_info["latitude"],
                    "longitude": place_info["longitude"],
                    "top_attractions": place_info["top_attractions"],
                    "hidden_gems": place_info["hidden_gems"],
                    "local_culture": place_info["local_culture"],
                    "traditional_clothing": place_info["traditional_clothing"],
                    "cultural_experiences": place_info["cultural_experiences"],
                    "shopping_spots": place_info["shopping_spots"],
                    "local_tips": place_info["local_tips"],
                    "restaurants": place_info["restaurants"],
                    "hospitals": place_info["hospitals"],
                    "transport": place_info["transport"],
                    "yearly_weather": place_info["yearly_weather"],
                    "current_weather": place_info["current_weather"],
                    "forecast": place_info.get("forecast", []),
                    "best_time_to_visit": place_info.get("best_time_to_visit", ""),
                    "typical_costs": place_info.get("typical_costs", {}),
                    "booking_links": place_info["booking_links"],
                    "shopping_links": place_info["shopping_links"],
                    "images": place_images
                })
                locations.append([place_info["longitude"], place_info["latitude"]])

            # Check if we have any valid places
            if not all_places_info:
                error_msg = "Could not find valid coordinates for any of the specified places."
                if failed_places:
                    error_msg += f" Failed places: {', '.join(failed_places)}"
                return render(request, "AI_trip.html", {"error": error_msg})

            # Show warning for failed places but continue with valid ones
            warning_msg = None
            if failed_places:
                warning_msg = f"Note: Could not find coordinates for {', '.join(failed_places)}. Continuing with other destinations."

            # Compute shortest path and routes (only if multiple places)
            path = [0]
            routes = []
            total_distance = 0
            route_points = []
            transport_info = []
            if len(locations) > 1:
                path, routes, total_distance, route_points = compute_shortest_path(locations)
            
            ordered_places = [all_places_info[i] for i in path]

            # Calculate budget per person for transport recommendations
            budget_per_person = budget / members

            # Compute transport info (only if multiple places)
            if len(ordered_places) > 1:
                client = Client(key=ORS_API_KEY)
                for i in range(len(path) - 1):
                    idx = path[i]
                    next_idx = path[i + 1]
                    try:
                        # First try to get accurate distances using Gemini
                        from_place = ordered_places[i]["name"]
                        to_place = ordered_places[i+1]["name"]
                        
                        distance_prompt = ChatPromptTemplate.from_template("""
                        What is the accurate road distance in kilometers and typical travel duration by car between {from_place} and {to_place} in India?
                        Provide only the numeric values in this exact format: "distance_km,duration_hours"
                        For example: "235.5,4.2"
                        """)
                        
                        distance_chain = distance_prompt | model | StrOutputParser()
                        try:
                            distance_response = distance_chain.invoke({"from_place": from_place, "to_place": to_place})
                            distance_parts = distance_response.strip().split(',')
                            if len(distance_parts) == 2:
                                try:
                                    distance_km = float(distance_parts[0])
                                    duration_hours = float(distance_parts[1])
                                    # Validate the values are reasonable
                                    if 1 <= distance_km <= 3000 and 0.1 <= duration_hours <= 50:
                                        # Use Gemini-provided values
                                        logger.info(f"Using Gemini distances: {from_place} to {to_place}: {distance_km}km, {duration_hours}h")
                                    else:
                                        # Fall back to ORS if values seem unreasonable
                                        raise ValueError("Unreasonable distance values")
                                except (ValueError, TypeError):
                                    # Fall back to ORS
                                    raise ValueError("Invalid distance format")
                            else:
                                # Fall back to ORS
                                raise ValueError("Invalid distance response format")
                        except Exception as e:
                            logger.warning(f"Falling back to ORS for distance: {e}")
                            # Fall back to ORS distance matrix
                            distance_matrix = client.distance_matrix(
                                locations=[locations[idx], locations[next_idx]],
                                profile='driving-car',
                                metrics=['distance', 'duration'],
                                units='km'
                            )
                            distance_km = distance_matrix['distances'][0][1]
                            duration_hours = distance_matrix['durations'][0][1] / 3600 if distance_matrix['durations'][0][1] is not None else 0
                            distance_km = distance_km / 1000 if distance_km is not None else 0
                    except exceptions.ApiError:
                        distance_km = 0
                        duration_hours = 0
                    
                    # Get transport recommendations with budget consideration
                    transport_rec = recommend_transport(distance_km, duration_hours, budget_per_person)
                    
                    transport_info.append({
                        "from": ordered_places[i]["name"],
                        "to": ordered_places[i+1]["name"],
                        "distance": f"{distance_km:.1f} km",
                        "duration": f"{duration_hours:.1f} hours",
                        "mode": transport_rec["mode"],
                        "options": transport_rec["options"],
                        "route_points": route_points[i] if i < len(route_points) else []
                    })

            # Add distance information to each place (only if multiple places)
            if len(ordered_places) > 1:
                for i, place in enumerate(ordered_places):
                    place["distances"] = []
                    for j, other_place in enumerate(ordered_places):
                        if i != j:
                            # Find the transport info between these places
                            transport = next((t for t in transport_info if t["from"] == place["name"] and t["to"] == other_place["name"]), None)
                            if transport:
                                place["distances"].append({
                                    "to": other_place["name"],
                                    "distance": transport["distance"],
                                    "duration": transport["duration"]
                                })

            # Generate daily plan with start date and budget consideration
            daily_plan = create_daily_plan(ordered_places, transport_info, days, start_date, budget_per_person)

            # Create travel path (only if multiple places)
            travel_path = " ➡️ ".join([p["name"] for p in ordered_places]) + " (Optimized route)" if len(ordered_places) > 1 else ordered_places[0]["name"]

            # Calculate budget breakdown
            budget_analysis = calculate_budget_breakdown(budget, days, members, ordered_places)

            context = {
                "days": days,
                "members": members,
                "budget": budget,
                "start_date": start_date.strftime("%d %b %Y") if start_date else "",
                "end_date": end_date.strftime("%d %b %Y") if end_date else "",
                "travel_path": travel_path,
                "places": ordered_places,
                "daily_plan": daily_plan,
                "routes": routes,
                "transport_info": transport_info,
                "total_distance": f"{total_distance:.1f} km",
                "budget_per_person": budget_analysis["budget_per_person"],
                "budget_per_day": budget_analysis["budget_per_day"],
                "budget_breakdown": budget_analysis["budget_breakdown"],
                "total_estimated_expenses": budget_analysis["total_estimated_expenses"],
                "remaining_budget": budget_analysis["remaining_budget"],
                "budget_tips": budget_analysis["budget_tips"]
            }
            
            # Add warning message if any places failed
            if warning_msg:
                context["warning"] = warning_msg
                
            return render(request, "AI_trip.html", context)

        except ValueError as e:
            return render(request, "AI_trip.html", {"error": str(e)})
        except Exception as e:
            logger.error(f"Unexpected error in AI_trip: {e}", exc_info=True)
            return render(request, "AI_trip.html", {"error": "An unexpected error occurred while planning the trip."})

    return render(request, "AI_trip.html")

@csrf_exempt
def home(request):
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        uploaded_image = request.FILES.get('image')
        
        # For images, we'll check if it's tourism-related after processing
        # For text-only messages, check if tourism/weather related
        if not uploaded_image and not is_tourism_or_weather_related(user_message):
            return JsonResponse({
                'response': "I can only help with tourism and weather-related questions. Please ask me about Indian destinations, travel planning, attractions, or weather information."
            })
        
        # Check if the message is a navigation request
        navigation_url = None
        message_lower = user_message.lower()
        
        # Check for "Take me to" or "Open" commands
        for route in ROUTES:
            if (f"take me to {route['name']}" in message_lower or 
                f"open {route['name']}" in message_lower or
                message_lower == route['name']):
                navigation_url = route['url']
                break
        
        if navigation_url:
            return JsonResponse({
                'response': f"I'll take you to the {user_message.replace('take me to ', '').replace('open ', '')} page.",
                'navigation': navigation_url
            })
        
        # Process the message with Gemini API
        try:
            # Configure Gemini
            genai.configure(api_key="AIzaSyB4QwG3zKnXUOA8gkV_6myyL3p9YO2zFAA")
            
            # Choose the appropriate model based on whether there's an image
            if uploaded_image:
                # Save uploaded image temporarily
                file_name = default_storage.save(f"temp_images/{uploaded_image.name}", ContentFile(uploaded_image.read()))
                image_path = default_storage.path(file_name)
                
                try:
                    # Check if the image is tourism-related
                    if not is_likely_tourism_image(image_path):
                        default_storage.delete(file_name)
                        return JsonResponse({
                            'response': "I can only analyze tourism and weather-related images. Please upload images of landmarks, destinations, tourist attractions, or travel-related content."
                        })
                    
                    # Use vision model for image analysis
                    model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17")
                    with open(image_path, "rb") as img_file:
                        image_data = img_file.read()
                    
                    # Create comprehensive tourism image analysis prompt
                    tourism_prompt = create_tourism_image_prompt(user_message)
                    
                    response = model.generate_content([
                        tourism_prompt,
                        {"mime_type": f"image/{Path(image_path).suffix[1:]}", "data": image_data}
                    ])
                    
                    # Clean up temporary file
                    default_storage.delete(file_name)
                    
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    if 'file_name' in locals():
                        try:
                            default_storage.delete(file_name)
                        except:
                            pass
                    return JsonResponse({'response': f"Sorry, I couldn't process that image. Error: {str(e)}"})
            else:
                # Use text-only model for regular queries
                model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17")
                
                # Create restricted prompt
                restricted_prompt = create_restricted_prompt(user_message, is_image=False)
                
                response = model.generate_content(restricted_prompt)
            
            # Extract the response text
            result = response.text if hasattr(response, 'text') else str(response)
            
            # For text-only queries, double-check if the response is appropriate
            if not uploaded_image and not is_tourism_or_weather_related(user_message) and "I can only help with tourism and weather-related questions" not in result:
                result = "I can only help with tourism and weather-related questions. Please ask me about Indian destinations, travel planning, attractions, or weather information."
            
            # Convert the response to Markdown format
            formatted_result = markdown.markdown(result)
            
            return JsonResponse({'response': formatted_result})
            
        except Exception as e:
            logger.error(f"Error in chat processing: {e}")
            return JsonResponse({'response': f"Sorry, I encountered an error: {str(e)}"})

    return render(request, 'home.html')

@csrf_exempt
def arvr(request):
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        uploaded_image = request.FILES.get('image')
        
        # For images, we'll check if it's tourism-related after processing
        # For text-only messages, check if tourism/weather related
        if not uploaded_image and not is_tourism_or_weather_related(user_message):
            return JsonResponse({
                'response': "I can only help with tourism and weather-related questions. Please ask me about Indian destinations, travel planning, attractions, or weather information."
            })
        
        # Check if the message is a navigation request
        navigation_url = None
        message_lower = user_message.lower()
        
        # Check for "Take me to" or "Open" commands
        for route in ROUTES:
            if (f"take me to {route['name']}" in message_lower or 
                f"open {route['name']}" in message_lower or
                message_lower == route['name']):
                navigation_url = route['url']
                break
        
        if navigation_url:
            return JsonResponse({
                'response': f"I'll take you to the {user_message.replace('take me to ', '').replace('open ', '')} page.",
                'navigation': navigation_url
            })
        
        # Process the message with Gemini API
        try:
            # Configure Gemini
            genai.configure(api_key="AIzaSyB4QwG3zKnXUOA8gkV_6myyL3p9YO2zFAA")
            
            # Choose the appropriate model based on whether there's an image
            if uploaded_image:
                # Save uploaded image temporarily
                file_name = default_storage.save(f"temp_images/{uploaded_image.name}", ContentFile(uploaded_image.read()))
                image_path = default_storage.path(file_name)
                
                try:
                    # Check if the image is tourism-related
                    if not is_likely_tourism_image(image_path):
                        default_storage.delete(file_name)
                        return JsonResponse({
                            'response': "I can only analyze tourism and weather-related images. Please upload images of landmarks, destinations, tourist attractions, or travel-related content."
                        })
                    
                    # Use vision model for image analysis
                    model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17")
                    with open(image_path, "rb") as img_file:
                        image_data = img_file.read()
                    
                    # Create AR/VR tourism image analysis prompt with enhanced cultural information
                    ar_vr_tourism_prompt = f"""
                    You are an AR/VR travel assistant for India. The user has uploaded an image and asked: "{user_message}"

                    Please analyze this tourism-related image and provide information about:

                    **LANDMARK/DESTINATION IDENTIFICATION:**
                    - What landmark, monument, or destination is shown?
                    - Location details and historical significance
                    - If it's a state capital or important administrative center

                    **CULTURAL & TRADITIONAL INFORMATION:**
                    - Local traditions and customs associated with this place
                    - Traditional festivals celebrated here
                    - Cultural significance and heritage value
                    - Traditional clothing and attire of the region
                    - Local art forms, music, and dance traditions
                    - Historical importance and cultural legacy

                    **AR/VR EXPERIENCES AVAILABLE:**
                    - Virtual reality tours available for this location
                    - Augmented reality apps that enhance the experience
                    - 360-degree virtual experiences and online tours
                    - Interactive digital guides and apps
                    - AR experiences that showcase cultural traditions

                    **IMMERSIVE TECHNOLOGY OPPORTUNITIES:**
                    - How visitors can use AR to learn more about the site
                    - VR experiences that recreate historical periods
                    - Digital reconstruction and virtual walkthroughs
                    - Mobile apps with AR features for this location
                    - Virtual cultural experiences and traditional performances

                    **VIRTUAL TOURISM OPTIONS:**
                    - Online virtual tours and experiences
                    - Live streaming tours and virtual guides
                    - Interactive museum experiences and digital exhibits
                    - Social VR experiences for group virtual visits
                    - Virtual cultural festivals and traditional celebrations

                    **TRAVEL PLANNING WITH TECHNOLOGY:**
                    - AR navigation apps for getting around
                    - VR previews before actual visits
                    - Digital travel planning tools
                    - Smart tourism technologies available at the site
                    - Apps that provide cultural and traditional information

                    Focus on how technology enhances the tourism experience at this destination, with special emphasis on cultural traditions and heritage.
                    """
                    
                    response = model.generate_content([
                        ar_vr_tourism_prompt,
                        {"mime_type": f"image/{Path(image_path).suffix[1:]}", "data": image_data}
                    ])
                    
                    # Clean up temporary file
                    default_storage.delete(file_name)
                    
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    if 'file_name' in locals():
                        try:
                            default_storage.delete(file_name)
                        except:
                            pass
                    return JsonResponse({'response': f"Sorry, I couldn't process that image. Error: {str(e)}"})
            else:
                # Use text-only model for regular queries with AR/VR context but restricted to tourism
                model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17")
                
                # Add AR/VR context to the user's message but restrict to tourism with enhanced cultural focus
                ar_vr_context = f"""
                You are an AR/VR travel assistant specializing in immersive experiences in India that ONLY provides information about:
                1. Tourism and travel-related AR/VR experiences
                2. Weather information for travel planning
                3. Virtual tourism and immersive travel technologies
                4. Cultural traditions, customs, and heritage information
                5. State capitals and administrative information related to travel

                User question: "{user_message}"

                IMPORTANT RESTRICTIONS:
                - If the question is NOT related to tourism or weather, respond with: "I can only help with tourism and weather-related questions. Please ask me about Indian destinations, travel planning, attractions, or weather information."
                - Only provide information about travel, tourism, destinations, weather, cultural traditions, and related AR/VR technologies
                - Do not answer questions about other subjects unless they are directly related to travel and tourism

                If the question is tourism/weather related, please provide information about:
                - AR/VR experiences available for Indian destinations
                - Virtual tours and immersive technologies for travel
                - How to experience Indian culture through AR/VR
                - Recommendations for virtual travel experiences
                - Cultural traditions, customs, festivals, and heritage information
                - State capitals and their significance for travelers
                - Traditional clothing, food, art forms, and local customs
                - Historical significance and cultural importance of places
                - Local festivals, celebrations, and cultural events
                - Virtual cultural experiences and traditional performances
                - AR/VR apps that showcase cultural traditions and heritage
                
                Keep responses focused on augmented reality, virtual reality, and immersive travel technologies while emphasizing cultural and traditional aspects.
                """
                
                response = model.generate_content(ar_vr_context)
            
            # Extract the response text
            result = response.text if hasattr(response, 'text') else str(response)
            
            # For text-only queries, double-check if the response is appropriate
            if not uploaded_image and not is_tourism_or_weather_related(user_message) and "I can only help with tourism and weather-related questions" not in result:
                result = "I can only help with tourism and weather-related questions. Please ask me about Indian destinations, travel planning, attractions, or weather information."
            
            # Convert the response to Markdown format
            formatted_result = markdown.markdown(result)
            
            return JsonResponse({'response': formatted_result})
            
        except Exception as e:
            logger.error(f"Error in AR/VR chat processing: {e}")
            return JsonResponse({'response': f"Sorry, I encountered an error: {str(e)}"})

    return render(request, 'arvr.html')

# All other view functions remain the same...
def allmap(request):
    return render(request, 'allmap.html')

def clickablemap(request):
    return render(request, 'clickablemap.html')

def westbengal(request):
    return render(request, 'westbengal.html')

def wb_7days(request):
    return render(request, 'wb_7days.html')

def wb_12days(request):
    return render(request, 'wb_12days.html')

def andhrapradesh(request):
    return render(request, 'andhrapradesh.html')

def andhrapradesh_7days(request):
    return render(request, 'andhrapradesh_7days.html')

def andhrapradesh_12days(request):
    return render(request, 'andhrapradesh_12days.html')

def arunachalpradesh(request):
    return render(request, 'arunachalpradesh.html')

def arunachalpradesh_7days(request):
    return render(request, 'arunachalpradesh_7days.html')

def arunachalpradesh_12days(request):
    return render(request, 'arunachalpradesh_12days.html')

def assam(request):
    return render(request, 'assam.html')

def assam_7days(request):
    return render(request, 'assam_7days.html')

def assam_12days(request):
    return render(request, 'assam_12days.html')

def bihar(request):
    return render(request, 'bihar.html')

def bihar_7days(request):
    return render(request, 'bihar_7days.html')

def bihar_12days(request):
    return render(request, 'bihar_12days.html')

def chattisgarh(request):
    return render(request, 'chattisgarh.html')

def chattisgarh_7days(request):
    return render(request, 'chattisgarh_7days.html')

def chattisgarh_12days(request):
    return render(request, 'chattisgarh_12days.html')

def goa(request):
    return render(request, 'goa.html')

def goa_7days(request):
    return render(request, 'goa_7days.html')

def goa_12days(request):
    return render(request, 'goa_12days.html')

def gujarat(request):
    return render(request, 'gujarat.html')

def gujarat_7days(request):
    return render(request, 'gujarat_7days.html')

def gujarat_12days(request):
    return render(request, 'gujarat_12days.html')

def haryana(request):
    return render(request, 'haryana.html')

def haryana_7days(request):
    return render(request, 'haryana_7days.html')

def haryana_12days(request):
    return render(request, 'haryana_12days.html')

def himachalpradesh(request):
    return render(request, 'himachalpradesh.html')

def himachalpradesh_7days(request):
    return render(request, 'himachalpradesh_7days.html')

def himachalpradesh_12days(request):
    return render(request, 'himachalpradesh_12days.html')

def eq_weather2(request):
    return render(request, 'eq_weather2.html')

def itmapalt(request):
    return render(request, 'itmapalt.html')

def jharkhand(request):
    return render(request, 'jharkhand.html')

def jharkhand_7days(request):
    return render(request, 'jharkhand_7days.html')

def jharkhand_12days(request):
    return render(request, 'jharkhand_12days.html')

def jammuandkashmir(request):
    return render(request, 'jammuandkashmir.html')

def kashmir_7days(request):
    return render(request, 'kashmir_7days.html')

def kashmir_12days(request):
    return render(request, 'kashmir_12days.html')

def Karnataka(request):
    return render(request, 'Karnataka.html')

def karnataka_7days(request):
    return render(request, 'karnataka_7days.html')

def karnataka_12days(request):
    return render(request, 'karnataka_12days.html')

def kerala(request):
    return render(request, 'kerala.html')

def kerala_7days(request):
    return render(request, 'kerala_7days.html')

def kerala_12days(request):
    return render(request, 'kerala_12days.html')

def madhyapradesh(request):
    return render(request, 'madhyapradesh.html')

def madhyapradesh_7days(request):
    return render(request, 'madhyapradesh_7days.html')

def madhyapradesh_12days(request):
    return render(request, 'madhyapradesh_12days.html')

def maharashtra(request):
    return render(request, 'maharashtra.html')

def maharashtra_7days(request):
    return render(request, 'maharashtra_7days.html')

def maharashtra_12days(request):
    return render(request, 'maharashtra_12days.html')

def manipur(request):
    return render(request, 'manipur.html')

def manipur_7days(request):
    return render(request, 'manipur_7days.html')

def manipur_12days(request):
    return render(request, 'manipur_12days.html')

def meghalaya(request):
    return render(request, 'meghalaya.html')

def meghalaya_7days(request):
    return render(request, 'meghalaya_7days.html')

def meghalaya_12days(request):
    return render(request, 'meghalaya_12days.html')

def mizoram(request):
    return render(request, 'mizoram.html')

def mizoram_7days(request):
    return render(request, 'mizoram_7days.html')

def mizoram_12days(request):
    return render(request, 'mizoram_12days.html')

def nagaland(request):
    return render(request, 'nagaland.html')

def nagaland_7days(request):
    return render(request, 'nagaland_7days.html')

def nagaland_12days(request):
    return render(request, 'nagaland_12days.html')

def odisha(request):
    return render(request, 'odisha.html')

def odisha_7days(request):
    return render(request, 'odisha_7days.html')

def odisha_12days(request):
    return render(request, 'odisha_12days.html')

def punjab(request):
    return render(request, 'punjab.html')

def punjab_7days(request):
    return render(request, 'punjab_7days.html')

def punjab_12days(request):
    return render(request, 'punjab_12days.html')

def rajasthan(request):
    return render(request, 'rajasthan.html')

def rajasthan_7days(request):
    return render(request, 'rajasthan_7days.html')

def rajasthan_12days(request):
    return render(request, 'rajasthan_12days.html')

def sikkim(request):
    return render(request, 'sikkim.html')

def sikkim_7days(request):
    return render(request, 'sikkim_7days.html')

def sikkim_12days(request):
    return render(request, 'sikkim_12days.html')

def tamilnadu(request):
    return render(request, 'tamilnadu.html')

def tamilnadu_7days(request):
    return render(request, 'tamilnadu_7days.html')

def tamilnadu_12days(request):
    return render(request, 'tamilnadu_12days.html')

def telangana(request):
    return render(request, 'telangana.html')

def telangana_7days(request):
    return render(request, 'telangana_7days.html')

def telangana_12days(request):
    return render(request, 'telangana_12days.html')

def tripura(request):
    return render(request, 'tripura.html')

def tripura_7days(request):
    return render(request, 'tripura_7days.html')

def tripura_12days(request):
    return render(request, 'tripura_12days.html')

def uttarakhand(request):
    return render(request, 'uttarakhand.html')

def uttarakhand_7days(request):
    return render(request, 'uttarakhand_7days.html')

def uttarakhand_12days(request):
    return render(request, 'uttarakhand_12days.html')

def uttarpradesh(request):
    return render(request, 'uttarpradesh.html')

def uttarpradesh_7days(request):
    return render(request, 'uttarpradesh_7days.html')

def uttarpradesh_12days(request):
    return render(request, 'uttarpradesh_12days.html')

def laksh(request):
    return render(request, 'laksh.html')

def laksh_7days(request):
    return render(request, 'laksh_7days.html')

def laksh_12days(request):
    return render(request, 'laksh_12days.html')

def newdel(request):
    return render(request, 'newdel.html')

def newdel_7days(request):
    return render(request, 'newdel_7days.html')

def newdel_12days(request):
    return render(request, 'newdel_12days.html')

def puducherry(request):
    return render(request, 'puducherry.html')

def puducherry_4days(request):
    return render(request, 'puducherry_4days.html')

def chandigarh(request):
    return render(request, 'chandigarh.html')

def chandigarh_4days(request):
    return render(request, 'chandigarh_4days.html')

def andamannicobar(request):
    return render(request, 'andamannicobar.html')

def andamannicobar_7days(request):
    return render(request, 'andamannicobar_7days.html')

def andamannicobar_12days(request):
    return render(request, 'andamannicobar_12days.html')

def dadraandnagarhaveli(request):
    return render(request, 'dadraandnagarhaveli.html')

def dadraandnagarhaveli_7days(request):
    return render(request, 'dadraandnagarhaveli_7days.html')

def dadraandnagarhaveli_12days(request):
    return render(request, 'dadraandnagarhaveli_12days.html')

def damananddiu(request):
    return render(request, 'damananddiu.html')

def damananddiu_7days(request):
    return render(request, 'damananddiu_7days.html')

def damananddiu_12days(request):
    return render(request, 'damananddiu_12days.html')

def ladakh(request):
    return render(request, 'ladakh.html')

def ladakh_7days(request):
    return render(request, 'ladakh_7days.html')

def ladakh_12days(request):
    return render(request, 'ladakh_12days.html')

def kashmir(request):
    return render(request, 'kashmir.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def mylocation(request):
    return render(request, 'mylocation.html')

def hp_7days_new(request):
    return render(request, 'hp_7days_new.html')

def recom(request):
    return render(request, 'recom.html')

def signup(request):
    return render(request, 'signup.html')

def bookings(request):
    return render(request, 'bookings.html')

@xframe_options_exempt
def bookbus(request):
    return render(request, 'bookbus.html')

@xframe_options_exempt
def bookcab(request):
    return render(request, 'bookcab.html')

@xframe_options_exempt
def bookflights(request):
    return render(request, 'bookflights.html')

@xframe_options_exempt
def bookhotels(request):
    return render(request, 'bookhotels.html')

@xframe_options_exempt
def booktrain(request):
    return render(request, 'booktrain.html')

def culture(request):
    return render(request, 'culture.html')

def adventure_tourism(request):
    return render(request, 'adventure_tourism.html')

def religious_tourism(request):
    return render(request, 'religious_tourism.html')

def mountain_tourism(request):
    return render(request, 'mountain_tourism.html')

def beach_vibes_tourism(request):
    return render(request, 'beach_vibes_tourism.html')

def wildlife_safaris_tourism(request):
    return render(request, 'wildlife_safaris_tourism.html')

def wellness_retreats_tourism(request):
    return render(request, 'wellness_retreats_tourism.html')

def culinary_journey_tourism(request):
    return render(request, 'culinary_journey_tourism.html')

def artisan_workshop_tourism(request):
    return render(request, 'artisan_workshop_tourism.html')

def Blog(request):
    return render(request, 'Blog.html')

def Gallery(request):
    return render(request, 'Gallery.html')

def shopping(request):
    return render(request, 'shopping.html')

def weather(request):
    return render(request, 'weather.html')

def crimenew(request):
    return render(request, 'crimenew.html')

def guidenew(request):
    return render(request, 'guidenew.html')

def seasonvisit(request):
    return render(request, 'seasonvisit.html')

def guideprofile(request):
    return render(request, 'guideprofile.html')