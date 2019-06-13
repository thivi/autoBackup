"""
Author: Theviyanthan K.
Github: https://github.com/thivi
Blog: http://thearmchaircritic.org
Linkedin: https://www.linkedin.com/in/krishnamohan-theviyanthan

Created Date: 13/06/2019

Command to execute: sudo python backup.py <backup/clean> <token> <dir>

Keys to be replaced:
    1. parentID: ID of the parent folder
    2. you@email.com: the email address of your gdrive
    3. zapierRestURL: Zapier rest api endpoint to send notificatiosn to
    
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import datetime
import io
import tarfile
import os
import sys
import requests
from pathlib import Path

def createDriveService(token):

    SCOPES=['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE=token

    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    return build('drive','v3',credentials=credentials)

def clearPastBackups(service): 
    page=None
    filesObj={}
    while True:
        files=service.files().list(q="mimeType='application/gzip' and name contains 'backup'",pageToken=page, fields="nextPageToken, files(id,name)").execute()

        for file in files.get('files',[]):
            filesObj[file.get('id')]=file.get('name')
        page=files.get('nextPageToken',None)
        if page is None:
            break

    if not(not filesObj or len(filesObj)<2):
        print("Two or more previous backups found.")
        latest=sorted(list(filesObj.values()))[len(filesObj)-1]
        
        for l in sorted(list(filesObj.values())):
            print(l)
        print ("Backup to be kept: %s."%latest)
        print("Deleting all but the latest backup...")
        for file in filesObj:
            if filesObj[file]!=latest:
                service.files().delete(fileId=file).execute()
                print("Backup named %s deleted."%filesObj[file])
   
def printFiles(service):
    print(service.files().list().execute().get('files',[]))

def removeAll(service):
    for file in service.files().list().execute().get('files',[]):
        service.files().delete(fileId=file.get('id')).execute()

def archive(dir):
    print("Archiving directory %s."%dir)
    now=datetime.datetime.now().isoformat().replace(':','_').split(".")[0]
    fileName="backup_"+now+".tar.bz2"
    with tarfile.open(fileName,"w:bz2") as tar:
        tar.add(dir)
        print("Directory successfully archived. Archive name: %s."%fileName)
        return fileName

def upload(fileName,service):
    print("Beginning backup upload...")
    media=MediaFileUpload(fileName,mimetype="application/gzip", resumable=True)

    file=service.files().create(body={'name':fileName,'parents':['parentID']},media_body=media,fields='id').execute()
    print("Backup uploaded. Online backup file ID is %s."%file.get('id'))
    print("Setting backup permissions...")
    def callback(request_id, response, exception):
        if exception:
            # Handle error
            print (exception)
        else:
            print ("Permission Id: %s" % response.get('id'))
    batch = service.new_batch_http_request(callback=callback)
    user_permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': 'you@email.com'
    }
    batch.add(service.permissions().create(
            fileId=file.get('id'),
            body=user_permission,
            fields='id',
    ))
    batch.execute() 

def clean():
    print("Deleting temporary files...")
    os.remove(fileName)
    print("Temporary files deleted. Backup complete!")



def notify(status,desc,now):
    print("Sending you a notification!")
    url="zapierRestURL"
    if status:
        print(requests.get(url=url, params={"status":"Backup successful!","body":"A new backup was made to Google drive on %s successfully. The backup name is: %s."%(now,desc)}))
    else:
        print(requests.get(url=url,params={"status":"Backup failed!","body":"Backup failed on %s. Error: %s."%(now,desc)}))

if (len(sys.argv)>2):
    try:
        token=sys.argv[2]
        service=createDriveService(token)
        if(len(sys.argv)==4 and sys.argv[1]=="backup"):

            token=sys.argv[2]
            service=createDriveService(token)
            fileName=archive(Path(sys.argv[3]))
            clearPastBackups(service)
            upload(fileName,service)
            clean()
            date=datetime.datetime.now().strftime("%d %B, %Y (%A) at %I:%M %p")
            notify(True,fileName,date)
            
        elif(sys.argv[1]=="clean"):
            printFiles(service)
            removeAll(service)
        else:
            print("Argument format incorrect. The only arguments that can be used are 'backup' and 'clean'. Pass the token file as the secodn argument. If you choose backup, please specify the directory to back up as the third argument.")
    except Exception as e:
        date=datetime.datetime.now().strftime("%d %B, %Y (%A) at %I:%M %p")
        print(e)
        notify(False,e,date)
else:
    print("Error: The arguments passed are not enough. You can choose either 'clean' or 'backup'. Pass the token file as the secodn argument. If you choose backup, specify the directory to backup as the third argument.")
