# app/services/transcription/audio_utils.py
import os
from pydub import AudioSegment
import tempfile


def extract_audio_from_video(video_path: str, output_format: str = "mp3") -> str:
    """
    Extrae audio de un archivo de video.
    
    :param video_path: Ruta al archivo de video
    :param output_format: Formato de salida (mp3, wav, etc.)
    :return: Ruta al archivo de audio extraído
    """
    try:
        audio = AudioSegment.from_file(video_path)
        
        # Crear archivo temporal
        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(temp_dir, f"{base_name}_audio.{output_format}")
        
        audio.export(output_path, format=output_format)
        return output_path
    except Exception as e:
        raise Exception(f"Error extrayendo audio de video: {str(e)}")


def split_audio_file(file_path: str, max_size_mb: int = 24) -> list:
    """
    Divide un archivo de audio en chunks más pequeños.
    
    :param file_path: Ruta al archivo de audio
    :param max_size_mb: Tamaño máximo de cada chunk en MB
    :return: Lista de rutas a los archivos divididos
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size_mb <= max_size_mb:
        return [file_path]
    
    try:
        audio = AudioSegment.from_file(file_path)
        
        # Calcular duración de cada chunk
        num_chunks = int(file_size_mb / max_size_mb) + 1
        chunk_duration_ms = len(audio) // num_chunks
        
        chunks = []
        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        for i in range(num_chunks):
            start_ms = i * chunk_duration_ms
            end_ms = min((i + 1) * chunk_duration_ms, len(audio))
            
            chunk = audio[start_ms:end_ms]
            chunk_path = os.path.join(temp_dir, f"{base_name}_chunk_{i}.mp3")
            chunk.export(chunk_path, format="mp3")
            chunks.append(chunk_path)
        
        return chunks
    except Exception as e:
        raise Exception(f"Error dividiendo archivo de audio: {str(e)}")


def is_video_file(file_path: str) -> bool:
    """Detecta si un archivo es video basado en su extensión."""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in video_extensions


def is_audio_file(file_path: str) -> bool:
    """Detecta si un archivo es audio basado en su extensión."""
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in audio_extensions


def prepare_for_transcription(file_path: str) -> list:
    """
    Prepara un archivo para transcripción:
    - Si es video, extrae el audio
    - Si es muy grande, lo divide en chunks
    
    :param file_path: Ruta al archivo original
    :return: Lista de archivos listos para transcribir
    """
    # Si es video, extraer audio
    if is_video_file(file_path):
        audio_path = extract_audio_from_video(file_path)
        file_path = audio_path
    
    # Dividir si es necesario (límite de 25MB para APIs)
    chunks = split_audio_file(file_path, max_size_mb=24)
    
    return chunks