import asyncio
import hashlib
import hmac
import shutil
from typing import Optional
from urllib.parse import urlencode
from fastapi import UploadFile
import os
from datetime import datetime, time
from src.config import settings
import boto3
from fastapi import UploadFile
import re
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError 


class FileHelper:
    def __init__(self):
        pass
    
    
    ###########################################
    ###########################################
    ########    Main STORAGE   ################
    ###########################################
    ###########################################
    
    @staticmethod
    async def upload_file(file: UploadFile, location: str = "", name: str = ""):
        """
        Upload a file to the specified location.

        If STORAGE_LOCATION is set to "local", this will save the file to the local
        file system. Otherwise, it will upload the file to AWS S3.

        Args:
            file (UploadFile): The file to be uploaded
            location (str): The directory path where the file should be
                uploaded. Defaults to "".
            name (str): The desired name of the uploaded file. Defaults to "".

        Returns:
            A tuple containing the URL of the uploaded file, the sanitized
            filename without extension, and the content type of the uploaded
            file. If `public` is False, the URL is the S3 key of the uploaded
            file instead of the public URL.
        """
        
        if settings.STORAGE_LOCATION == "local":
            return await FileHelper.upload_file_local(file, location, name)
        else:
            return await FileHelper.upload_file_to_s3(file, location, name, public=True)

    @staticmethod
    async def upload_private_file(file: UploadFile, location: str = "", name: str = "", extension: Optional[str] = None):
        """
        Upload a private file to the specified location.

        If STORAGE_LOCATION is set to "local", this will save the file to the local
        file system. Otherwise, it will upload the file to AWS S3 with private access.

        Args:
            file (UploadFile): The file to be uploaded.
            location (str, optional): The directory path where the file should be
                uploaded. Defaults to "".
            name (str, optional): The desired name of the uploaded file. Defaults to "".
            extension (Optional[str], optional): The file extension. Defaults to None.

        Returns:
            A tuple containing the path or URL of the uploaded file, the sanitized
            filename without extension, and the content type of the uploaded file.
        """

        if settings.STORAGE_LOCATION == "local":
            return await FileHelper.upload_private_file_local(file, location, name)
        else:
            return await FileHelper.upload_file_to_s3(file, location, name, False )
    
    @staticmethod
    def delete_file(file_path: Optional[str] = None):
        """
        Delete a file from the specified storage location.

        If STORAGE_LOCATION is set to "local", it deletes the file from the local
        file system. Otherwise, it deletes the file from AWS S3.

        Args:
            file_path (Optional[str]): The path or key of the file to be deleted.
                If None or an empty string, the function will not perform any action.
        """

        if file_path is None or file_path == "":
            return
        if settings.STORAGE_LOCATION == "local":
            return FileHelper.delete_file_local(file_path)
        else:
            return FileHelper.delete_file_from_s3(file_path)
    
    
    @staticmethod
    def delete_folder(file_path: Optional[str] = None):
        
        """
        Delete a folder from the specified storage location.

        If STORAGE_LOCATION is set to "local", it deletes the folder from the local
        file system. Otherwise, it deletes the folder from AWS S3.

        Args:
            file_path (Optional[str]): The path or key of the folder to be deleted.
                If None or an empty string, the function will not perform any action.
        """
        
        if file_path is None or file_path == "":
            return
        if "uploads" in file_path:
            return FileHelper.delete_local_folder(file_path)
        else:
            return FileHelper.delete_s3_folder(file_path)
    
    @staticmethod
    async def upload_private_byte(file: bytes, location: str = "", name: str = "", content_type: Optional[str] = None):
        """
        Upload a private byte stream to the specified location.

        If STORAGE_LOCATION is set to "local", this will save the byte stream 
        to the local file system. Otherwise, it will upload the byte stream 
        to AWS S3 with private access.

        Args:
            file (bytes): The byte stream to be uploaded.
            location (str, optional): The directory path where the byte stream 
                should be uploaded. Defaults to "".
            name (str, optional): The desired name of the uploaded file. Defaults to "".
            content_type (Optional[str], optional): The MIME type of the byte stream. 
                Defaults to None.

        Returns:
            A tuple containing the path or URL of the uploaded file, the sanitized
            filename without extension, and the content type of the uploaded file.
        """

        if settings.STORAGE_LOCATION == "local":
            return await FileHelper.upload_private_byte_local(file, location, name, content_type)
        else:
            return await FileHelper.upload_byte_to_s3(file, location, name, False , content_type=content_type)
    
    
    @staticmethod
    async def upload_public_byte(file: bytes, location: str = "", name: str = "", content_type: Optional[str] = None):
    
        if settings.STORAGE_LOCATION == "local":
            return await FileHelper.upload_public_byte_local(file, location, name, content_type)
        else:
            return await FileHelper.upload_byte_to_s3(file, location, name, True , content_type=content_type)
    
    ###########################################
    ###########################################
    ########  AWS S3 STORAGE   ################
    ###########################################
    ###########################################
    
    @staticmethod
    def get_s3_client():
        
        """
        Create and return an S3 client using the AWS credentials and region
        specified in the settings.

        Returns:
            boto3.S3.Client: The S3 client instance configured with the
            provided AWS access key, secret access key, and region.
        """

        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

    @staticmethod
    def sanitize_filename(name: Optional[str]=None) -> str:
        """
        Sanitize a given filename by replacing invalid characters with underscores.

        Args:
            name (str): The original filename to be sanitized.

        Returns:
            str: A sanitized version of the filename with invalid characters replaced
            by underscores. Only alphanumeric characters, dashes, underscores, and
            periods are retained.
        """
        
        if name is None:
            return ""
        return re.sub(r'[^\w\-_\.]', '_', name)


    @staticmethod
    async def upload_file_to_s3(file: UploadFile, location: str = "", name: str = "", public: bool = True):
        """
        Uploads a file to AWS S3.

        Args:
            file (UploadFile): The file to be uploaded.
            location (str, optional): The directory path where the file should be
                uploaded. Defaults to "".
            name (str, optional): The desired name of the uploaded file. Defaults to "".
            public (bool, optional): Whether the uploaded file should be publicly
                accessible. Defaults to True.

        Returns:
            A tuple containing the URL of the uploaded file, the sanitized filename
            without extension, and the content type of the uploaded file. If `public` is
            False, the URL is the S3 key of the uploaded file instead of the public URL.

        Raises:
            ValueError: If the file size exceeds the maximum allowed size.
            RuntimeError: If AWS credentials are missing or invalid, or if the S3 upload
                fails.
        """
        try:
            if file.size > settings.MAX_FILE_SIZE:
                raise ValueError(f"File size exceeds limit of {settings.MAX_FILE_SIZE} bytes")

            path = location.strip("/")
            date_time_now = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_split = os.path.splitext(file.filename)

            if not name or name == "":
                back_name = FileHelper.sanitize_filename(name_split[0]) 
                name = back_name + "_s3" + name_split[1]
            else:
                back_name = FileHelper.sanitize_filename(name)
                name = f"{back_name}_s3{name_split[1]}"

            full_path = f"{path}/{date_time_now}_{name}" if path else f"{date_time_now}_{name}"
            
            extra_args = { "ContentType": file.content_type }
        
            if public:
                full_path = f"public/{full_path}"
            else : 
                full_path = f"private/{full_path}"
                
            file.file.seek(0)
            s3 = FileHelper.get_s3_client()
            
            s3.upload_fileobj(file.file, settings.AWS_BUCKET_NAME, full_path, ExtraArgs=extra_args)

            public_url = f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{full_path}"

            return (public_url if public else full_path), back_name, file.content_type

        except NoCredentialsError:
            raise RuntimeError("AWS credentials are missing or invalid")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchBucket":
                raise RuntimeError(f"Bucket {settings.AWS_BUCKET_NAME} does not exist")
            raise RuntimeError(f"S3 upload failed: {str(e)}")
        except BotoCoreError as e:
            raise RuntimeError(f"S3 error: {str(e)}")
    
    
    
    @staticmethod
    async def upload_byte_to_s3(file: bytes, location: str = "", name: str = "", public: bool = True,content_type : Optional[str]=None):
        
        try:
            if len(file) > settings.MAX_FILE_SIZE:
                raise ValueError(f"File size exceeds limit of {settings.MAX_FILE_SIZE} bytes")

            path = location.strip("/")
            
            name_split = os.path.splitext(name)

            name = f"{name_split[0]}_s3{name_split[1]}"


            full_path = f"{path}/{name}" if path else f"{name}"
        
            if public:
                full_path = f"public/{full_path}"
            else : 
                full_path = f"private/{full_path}"
                

            s3 = FileHelper.get_s3_client()
            s3.put_object(Bucket=settings.AWS_BUCKET_NAME, Key=full_path, Body=file, ContentType=content_type)
        
            public_url = FileHelper.get_s3_public_url(full_path)

            return (public_url if public else full_path), name, content_type

        except NoCredentialsError:
            raise RuntimeError("AWS credentials are missing or invalid")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchBucket":
                raise RuntimeError(f"Bucket {settings.AWS_BUCKET_NAME} does not exist")
            raise RuntimeError(f"S3 upload failed: {str(e)}")
        except BotoCoreError as e:
            raise RuntimeError(f"S3 error: {str(e)}")
    
    
    
    
    @staticmethod
    def delete_s3_folder(prefix: str):
        """
        Delete all objects in an S3 bucket that start with a given prefix.

        Given a prefix string, this function lists all objects in the
        S3 bucket that start with that prefix, and then deletes them.

        Parameters:
        prefix (str): The prefix to match objects against.

        Returns:
        None
        """
        s3 = FileHelper.get_s3_client()
        response = s3.list_objects_v2(Bucket=settings.AWS_BUCKET_NAME, Prefix=prefix)
        if "Contents" in response:
            for obj in response["Contents"]:
                s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=obj["Key"])
                print(f"🗑 Deleted {obj['Key']}")

    @staticmethod
    def delete_file_from_s3(key: str) -> bool:
        """
        Delete a file from an S3 bucket.

        Args:
            key (str): The S3 key (path) of the file to delete (e.g., 'folder/20250710_183045_example.txt').

        Returns:
            bool: True if the file was deleted successfully, False if the file was not found.

        Raises:
            RuntimeError: If AWS credentials are missing or another S3 error occurs.
        """
        try:
            s3 = FileHelper.get_s3_client()
            s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=key.strip("/"))
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return False  # File doesn't exist
            raise RuntimeError(f"Failed to delete file from S3: {str(e)}")
        except NoCredentialsError:
            raise RuntimeError("AWS credentials not found")
        except BotoCoreError as e:
            raise RuntimeError(f"S3 error: {str(e)}")
    
    @staticmethod
    def get_s3_public_url(key: str):
        """
        Return the public URL for a file stored in an S3 bucket.

        Parameters:
        key (str): The S3 key (path) of the file to get the URL for (e.g., 'folder/20250710_183045_example.txt').

        Returns:
        str: The public URL for the given file.
        """
        return f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    @staticmethod
    def generate_s3_presigned_url(key: str, expires_in: int = 3600):
        """
        Generate a presigned URL for a file stored in an S3 bucket.

        This method creates a presigned URL that can be used to access a file
        in an S3 bucket for a limited amount of time without requiring AWS credentials.

        Args:
            key (str): The S3 key (path) of the file to generate the URL for (e.g., 'folder/20250710_183045_example.txt').
            expires_in (int, optional): The number of seconds the presigned URL is valid for. Defaults to 3600 seconds (1 hour).

        Returns:
            str: The generated presigned URL if successful; otherwise, None if the file does not exist.

        Raises:
            RuntimeError: If an error occurs during URL generation, such as missing AWS credentials or a client error.
        """

        try:
            s3 = FileHelper.get_s3_client()
            return s3.generate_presigned_url(
                "get_object",
                {"Bucket": settings.AWS_BUCKET_NAME, "Key": key},
                ExpiresIn=expires_in,
            )
            
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return None 
            raise RuntimeError(f"Could not generate presigned URL: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Could not generate presigned URL: {str(e)}")
        
        
    @staticmethod
    async def s3_stream(key: str, chunk_size: int = 4 * 1024 * 1024):
        s3 = FileHelper.get_s3_client()
        loop = asyncio.get_running_loop()
        s3_object = await loop.run_in_executor(None, lambda: s3.get_object(Bucket=settings.AWS_BUCKET_NAME, Key=key))
        body = s3_object["Body"]

        for chunk in body.iter_chunks(chunk_size):
            yield chunk
        
    @staticmethod
    def get_aws_object(key: str):
        
        """
        Get a file object from AWS S3.

        Given a key string, this function attempts to retrieve the
        corresponding file object from the S3 bucket specified in the
        settings. The file object is returned if successful; otherwise,
        `None` is returned if the file does not exist.

        Args:
            key (str): The S3 key (path) of the file to retrieve (e.g., 'folder/20250710_183045_example.txt').

        Returns:
            dict: The file object if successful; otherwise, None if the file does not exist.

        Raises:
            RuntimeError: If an error occurs during file retrieval, such as missing AWS credentials or a client error.
        """
        try:
            s3 = FileHelper.get_s3_client()
            return  s3.get_object(Bucket=settings.AWS_BUCKET_NAME, Key=key)
            
        except ClientError as e:
            print(e)
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                
                return None 
            raise RuntimeError(f"Could not get the object : {str(e)}")
        except Exception as e:
            print(e)
            raise RuntimeError(f"Could not get the object: {str(e)}")

    @staticmethod
    def get_aws_list_objects_v2(prefix: str):

        try:
            s3 = FileHelper.get_s3_client()
            return  s3.list_objects_v2(Bucket=settings.AWS_BUCKET_NAME, Prefix=prefix)
        
        except ClientError as e:
            print(e)
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                
                return None 
            raise RuntimeError(f"Could not get the object : {str(e)}")
        except Exception as e:
            print(e)
            raise RuntimeError(f"Could not get the object: {str(e)}")
        



    ###########################################
    ###########################################
    ########   LOCAL STORAGE   ################
    ###########################################
    ###########################################
    
    
    @staticmethod
    def generate_local_signed_url(file_path: str , expire: int) -> str:
        """
        Generates a signed URL that can be used to access a locally stored file.

        The returned URL will be valid for the specified number of seconds. If the
        URL is accessed after that time, it will be invalid.

        Args:
            file_path: The path to the file to generate the signed URL for.
            expire: The number of seconds the URL should remain valid for.

        Returns:
            str: The signed URL.

        Raises:
            RuntimeError: If an error occurs during URL generation, such as a client error.
        """
        
        expire = int(time.time()) + expire
        data = f"{file_path}:{expire}"
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        query = urlencode({
            "file": file_path,
            "expire": expire,
            "signature": signature
        })

        return f"/private-file?{query}"

    
    @staticmethod
    async def upload_file_local(file: UploadFile, location: str = "", name: str = ""):
        """
        This function is used to upload a file to the server. The file is saved
        in the src/static directory. If a location is provided, the file is saved
        in that location. If a name is provided, the file is saved with that name.
        Otherwise, the file is saved with the same name as the original file.

        Args:
            file (UploadFile): The file to be uploaded
            location (str): The location where the file should be saved
            name (str): The name with which the file should be saved

        Returns:
            A tuple containing the path of the saved file, the name of the saved
            file, and the content type of the file
        """
        try:
            path_save = "src/static/uploads"
            path_save = path_save + location

            if not os.path.exists(path_save):
                os.makedirs(path_save)

            path = "static/uploads" + location

            date_time_now = datetime.now().strftime("%H%M%S%f")
            name_split = os.path.splitext(file.filename)
            if name == "":
                name = file.filename
                back_name = name_split[0]
            else:
                back_name = name
                name = f"{name}{name_split[1]}"

            path = f"{path}/{date_time_now}_{name}"
            path_save = f"{path_save}/{date_time_now}_{name}"
            contents = await file.read()
            with open(path_save, "wb") as f:
                f.write(contents)

            return path, back_name, file.content_type

        except Exception as e:
            print(e)
            return None, None, None

    @staticmethod
    async def upload_private_file_local(file: UploadFile, location: str = "", name: str = ""):
        """
        This function is used to upload a file to the server. The file is saved
        in the src/static directory. If a location is provided, the file is saved
        in that location. If a name is provided, the file is saved with that name.
        Otherwise, the file is saved with the same name as the original file.

        Args:
            file (UploadFile): The file to be uploaded
            location (str): The location where the file should be saved
            name (str): The name with which the file should be saved

        Returns:
            A tuple containing the path of the saved file, the name of the saved
            file, and the content type of the file
        """
        try:
            path_save = "src/uploads"
            path_save = path_save + location

            if not os.path.exists(path_save):
                os.makedirs(path_save)

            path = "uploads" + location

            date_time_now = datetime.now().strftime("%H%M%S%f")
            name_split = os.path.splitext(file.filename)
            if name == "":
                name = file.filename
                back_name = name_split[0]
            else:
                back_name = name
                name = f"{name}{name_split[1]}"

            path = f"{path}/{date_time_now}_{name}"
            path_save = f"{path_save}/{date_time_now}_{name}"
            with open(path_save, "wb") as f:
                f.write(file.file.read())

            extension = file.content_type
            return path, back_name, extension

        except Exception as e:
            print(e)
            return None, None, None
    
    @staticmethod
    async def upload_private_byte_local(file: bytes, location: str = "", name: str = "",extension: Optional[str] = None):
        
        """
        This function is used to upload a byte file to the server. The file is saved
        in the src/static directory. If a location is provided, the file is saved
        in that location. If a name is provided, the file is saved with that name.
        Otherwise, the file is saved with the same name as the original file.

        Args:
            file (bytes): The file to be uploaded
            location (str): The location where the file should be saved
            name (str): The name with which the file should be saved
            extension (Optional[str]): The content type of the file

        Returns:
            A tuple containing the path of the saved file, the name of the saved
            file, and the content type of the file
        """
        try:
            path_save = "src/uploads"
            path_save = path_save + location

            if not os.path.exists(path_save):
                try :
                    os.makedirs(path_save)
                except :
                    pass

            path = "uploads" + location

            path = f"{path}/{name}"
            path_save = f"{path_save}/{name}"
            with open(path_save, "wb") as f:
                f.write(file)
            
            return path, name, extension

        except Exception as e:
            print(e)
            return None, None, None
    
    @staticmethod
    async def upload_public_byte_local(file: bytes, location: str = "", name: str = "",extension: Optional[str] = None):
        
        try:
            path_save = "src/static/uploads"
            path_save = path_save + location

            if not os.path.exists(path_save):
                try :
                    os.makedirs(path_save)
                except :
                    pass

            path = "uploads" + location

            path = f"{path}/{name}"
            path_save = f"{path_save}/{name}"
            with open(path_save, "wb") as f:
                f.write(file)
            print(path_save)
            return path, name, extension

        except Exception as e:
            print(e)
            return None, None, None
    
    
    @staticmethod
    def delete_file_local(file_path: str):
        
        """
        This function is used to delete a file from the local server. The path to
        the file should be provided. The function returns a dictionary with the
        message and the success status.

        Args:
            file_path (str): The path to the file to be deleted

        Returns:
            A dictionary containing the message and the success status
        """
        try:
            # Construct the full path to the image
            full_path = os.path.join("src", file_path)

            # Check if the file exists
            if os.path.exists(full_path):
                os.remove(full_path)
                return {"message": "File deleted successfully", "success": True}
            else:
                return {"message": "File not found", "success": False}

        except Exception as e:
            print(e)
            return {"message": "Exception has occur", "success": False}

    @staticmethod
    def delete_local_folder(folder_path: str):
        """
        Deletes a folder from the local server.

        This function takes the relative path to a folder, constructs its absolute path,
        and deletes it if it exists. If the folder does not exist, a message indicating
        that the folder was not found is printed.

        Args:
            folder_path (str): The relative path to the folder to be deleted.
        """

        absolute_path = os.path.abspath("src/"+folder_path)
    
        if os.path.isdir(absolute_path):
            shutil.rmtree(absolute_path)
            print(f"🗑 Deleted local folder: {absolute_path}")
        else:
            print(f"⚠ Folder not found: {absolute_path}")