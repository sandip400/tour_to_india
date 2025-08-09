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

os.environ["GOOGLE_API_KEY"] = "AIzaSyCNyTPuez7O1LHQH70ehpUADDmMw7qozM0"


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
            genai.configure(api_key="AIzaSyCNyTPuez7O1LHQH70ehpUADDmMw7qozM0")
            
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
                    model = genai.GenerativeModel(model_name="gemini-2.5-pro")
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
                model = genai.GenerativeModel(model_name="gemini-2.5-pro")
                
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
            genai.configure(api_key="AIzaSyCNyTPuez7O1LHQH70ehpUADDmMw7qozM0")
            
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
                    model = genai.GenerativeModel(model_name="gemini-2.5-pro")
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
                model = genai.GenerativeModel(model_name="gemini-2.5-pro")
                
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


def weather(request):
    return render(request, 'weather.html')


def guidenew(request):
    return render(request, 'guidenew.html')

def seasonvisit(request):
    return render(request, 'seasonvisit.html')

def guideprofile(request):
    return render(request, 'guideprofile.html')