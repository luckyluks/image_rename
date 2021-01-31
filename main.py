import os
import sys
import time
from tqdm import tqdm
import datetime
from PIL import Image
import json

from argparse import ArgumentParser
from collections import Counter


# Set constants
VALID_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".aae"]
VALID_VIDEO_EXTENSIONS = [".mov", ".mp4"]


def build_argparser():
    """
    Parse command line arguments.
    :return: command line arguments
    """
    parser = ArgumentParser()
    parser.add_argument("-i", "--path_inputs", required=False, type=str,
                        help="Path folder of files")
    parser.add_argument("-o", "--path_outputs", required=False, type=str,
                        help="Path output folder")
    parser.add_argument("-l", "--log_file", required=False, type=str,
                        help="Log file name. Default (<date>_rename.log")
    parser.add_argument("-f", "--force", default=False, action="store_true",
                        help="Force file overwrite")
    return parser


def main():
    """
    Run
    :return: None
    """
    # Grab command line args
    args = build_argparser().parse_args()

    if args.path_inputs is None:
        root_folder_path = os.getcwd()
    else:
        root_folder_path = args.path_inputs

    if args.path_outputs is None:
        out_folder_path = os.path.join(root_folder_path, "out")
    else:
        out_folder_path = args.path_outputs

    # Get all files from folder
    # file_names = os.listdir(root_folder_path)
    file_names = [os.path.join(dp, f) for dp, dn, filenames in os.walk(root_folder_path) for f in filenames]

    start_time = datetime.datetime.now()
    if args.log_file is None:
        log_file_name = f"{start_time.strftime('%Y%m%d_%H%M%S')}_rename.log"
    else:
        log_file_name = args.log_file

    # count files
    total_files_count = len(file_names)
    image_files_count = len([fn for fn in file_names if os.path.splitext(fn)[1].lower() in VALID_IMAGE_EXTENSIONS])
    video_files_count = len([fn for fn in file_names if os.path.splitext(fn)[1].lower() in VALID_VIDEO_EXTENSIONS])
    files_to_skip =[fn for fn in file_names if not((os.path.splitext(fn)[1].lower() in VALID_IMAGE_EXTENSIONS) or (os.path.splitext(fn)[1].lower() in VALID_VIDEO_EXTENSIONS))]
    remaining_files_count = len(files_to_skip)
    skipped_extensions = [os.path.splitext(fn)[1].lower() for fn in files_to_skip]
    skipped_extensions = dict(zip(Counter(skipped_extensions).keys(), Counter(skipped_extensions).values()))
    
    # start_message = (
    #     f"{5*'='} python file rename script {50*'='}\n"
    #     f"started at: {start_time.strftime('%Y-%m-%d_%H:%M:%S')}\n"
    #     f"folder root to process: {root_folder_path}\n"
    #     f"number of files: total={total_files_count}, images={image_files_count}, videos={video_files_count}, others={remaining_files_count}\n"
    #     f"skipped file endings (and count) in files: {skipped_extensions}\n"
    #     f"\n"
    #     f"{5*'='} start renaming {50*'='}\n"
    # )
    # print(start_message)

    # a Python object (dict):
    start_message = {
        "description": "rename images/videos files for backup",
        "time_start": start_time.strftime('%Y-%m-%d_%H:%M:%S'),
        "root_folder": root_folder_path.replace('\\\\', '\\'),
        "file_counts": {
            "total": total_files_count,
            "images": image_files_count,
            "videos": video_files_count,
            "others": remaining_files_count,
        },
        "skipped_file_endings": skipped_extensions,
        "log_file_name": os.path.join(root_folder_path, log_file_name).replace('\\\\', '\\'),
        "file_changes": []
    }

    # convert into JSON:
    print(f"{json.dumps(start_message, indent=4, sort_keys=True)}\n")


    try:
        # For each file
        for file_name in tqdm(file_names):
            
            # default
            current_is_duplicate = False

            # Get the file extension
            file_ext = os.path.splitext(file_name)[1].lower()
            folder_path = os.path.dirname(file_name)

            # Create the old file path
            old_file_path = os.path.join(folder_path, file_name)

            # If the file does not have a valid file extension, then skip it
            if (file_ext in VALID_IMAGE_EXTENSIONS):
                file_type_prefix = "IMG_"
            elif (file_ext in VALID_VIDEO_EXTENSIONS):
                file_type_prefix = "VID_"
            else:
                skip_message = {"action": "skipped", "file_org": old_file_path.replace('\\\\', '\\'), "file_new": ""}
                print(f"{json.dumps(skip_message, sort_keys=True)}")
                # log_file.write(f"{skip_message}\n")
                start_message["file_changes"].append(skip_message)
                continue

            
            date_taken_str = ""
            date_oldest_str = ""

            creation_date = datetime.datetime.fromtimestamp(os.path.getctime(old_file_path))
            modification_date =  datetime.datetime.fromtimestamp(os.path.getmtime(old_file_path))

            try:
                # Open the image
                image = Image.open(old_file_path)
                # Get the date taken from EXIF metadata
                date_taken = image.getexif().get(36867)
                date_taken = datetime.datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
                date_taken_str = date_taken.strftime("%Y%m%d_%H%M%S")
                date_time_str = date_taken_str
                
            except Exception:

                date_out = min([creation_date, modification_date])
                date_oldest_str = date_out.strftime("%Y%m%d_%H%M%S")
                date_time_str = date_oldest_str
            finally:
                # Close the image
                image.close()

                # print(f"file '{old_file_path}' has no exif date. Use date '{date_out}' instead.")
            

            # Combine the new file name and file extension
            new_file_name = file_type_prefix + date_time_str + file_ext
            
            # Create the new folder path
            new_file_path = os.path.join(out_folder_path, new_file_name)
            unique_id = 1

            if file_type_prefix == "IMG_":

                while os.path.exists(new_file_path):

                    im_current = Image.open(old_file_path)
                    im_saved = Image.open(new_file_path)

                    if list(im_current.getdata()) == list(im_saved.getdata()):
                        duplicate_message = {"action": "skipped_duplicate", "file_org": old_file_path.replace('\\\\', '\\'), "file_new": new_file_path.replace('\\\\', '\\')}
                        # print(f"{json.dumps(duplicate_message, sort_keys=True)}")
                        start_message["file_changes"].append(duplicate_message)#
                        current_is_duplicate = True
                        break
                    else:
                        
                        new_file_path = os.path.join(out_folder_path, (file_type_prefix + date_time_str + f"-{unique_id}"+ file_ext))
                        unique_id += 1

                    im_current.close()
                    im_saved.close()

                    current_is_duplicate = False

                if current_is_duplicate:
                    continue

            else:
                while os.path.exists(new_file_path):
                    new_file_path = os.path.join(out_folder_path, (file_type_prefix + date_time_str + f"-{unique_id}"+ file_ext))
                    unique_id += 1


            # Rename the file
            os.rename(old_file_path, new_file_path)

            # print and write debug
            rename_message = {
                "action": "renamed",
                "file_org": old_file_path.replace('\\\\', '\\'),
                "file_new": new_file_path.replace('\\\\', '\\'),
                "exif_date": date_taken_str,
                "creation_date": creation_date.strftime("%Y%m%d_%H%M%S"),
                "modification_date": modification_date.strftime("%Y%m%d_%H%M%S"),
                "oldest_date": date_oldest_str
            }
            # print(f"{json.dumps(rename_message)}")
            # log_file.write(f"{rename_message}\n")
            start_message["file_changes"].append(rename_message)

        end_time = datetime.datetime.now()
        start_message["time_end"] = end_time.strftime('%Y-%m-%d_%H:%M:%S')
        start_message["time_elapsed"] = str((end_time - start_time).total_seconds())+"s"
    except Exception as e:
        print(f"in case of error: last_file_processed: {old_file_path}")
        print(e)
    finally:

        # create log file
        log_file = open(os.path.join(root_folder_path, log_file_name), "w")
        log_file.write(f"{json.dumps(start_message, indent=4, sort_keys=True)}\n\n")
        log_file.close() #This close() is important

if __name__ == '__main__':
    main()
    