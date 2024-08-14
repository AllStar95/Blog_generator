from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from pytube import YouTube
import os
import assemblyai as aai
import openai
import logging

# Configure logging (if not already configured in Django settings)
logger = logging.getLogger(__name__)

# Create your views here.
@login_required
def index(request):
    return render(request,'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except {KeyError, json.JSONDecodeError}:
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        
        # get yt title
        title = yt_title(yt_link)

        # get transcript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': "Failed to get a transcript"}, status= 500)

        # use openAI to generate blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to generate blog article"}, status= 500)

        # save blog article to db

        # return blog article as a response
        return JsonResponse({'content': blog_content})


    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio(link):
    try:
        # Initialize YouTube object
        yt = YouTube(link)
        
        # Filter audio-only streams and get the first one
        video = yt.streams.filter(only_audio=True).first()
        if not video:
            logger.error("No audio stream available")
            raise Exception("No audio stream available")

        # Download the file to the specified output path
        out_file = video.download(output_path=settings.MEDIA_ROOT)

        # Change file extension to .mp3
        base, ext = os.path.splitext(out_file)
        new_file = base + '.mp3'
        os.rename(out_file, new_file)

        return new_file
    except Exception as e:
        logger.error(f"An error occurred while downloading audio: {e}")
        return None

def get_transcription(link):
    audio_file = download_audio(link)
    
    if audio_file is None:
        print("Error: Audio download failed.")
        return None

    # Ensure you set the correct API key
    aai.settings.api_key = "your_actual_api_key_here"

    try:
        transcriber = aai.Transcriber()
        # Assuming the `transcribe` method takes the file path as an argument
        transcript = transcriber.transcribe(audio_file)
        return transcript.get('text', 'No transcription available')

    except Exception as e:
        print(f"Error: An error occurred during transcription - {e}")
        return None

def generate_blog_from_transcription(transcription):
    openai.api_key = "your-api-key"

    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"


    response = openai.Completion.create(
        model = "text-davinci-003",
        prompt = prompt,
        max_tokens = 1000
    )

    generated_content = response.choices[0].text.strip()

    return generated_content
def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username = username, password = password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {'error_message': error_message })
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']  
        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message': error_message})
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message': error_message})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')