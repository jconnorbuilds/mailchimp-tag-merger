from dotenv import load_dotenv
import os
import logging
import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError


load_dotenv()
logging.basicConfig(filename="logs/changes.log", encoding="utf-8", level=logging.INFO)

"""
---Config---
api_key: your Mailchimp Marketing API key
list_id: The list ID of the list (or audience) you want to use
server: (ex. us11) The server prefix at the beginning of your mailchimp url 
"""
api_key = os.getenv("MAILCHIMP_API_KEY")
list_id = os.getenv("MAILCHIMP_LIST_ID")
server = os.getenv("SERVER_PREFIX")

client = MailchimpMarketing.Client()
client.set_config({"api_key": api_key, "server": server})

OLD_TAGS = [
    "event: Chamomile and Whiskey, Will Overman at Toast",
    "event: Will Overman Band Farewell Block Party & EP Release",
    "event: Will Overman Block Party",
]
NEW_TAGS = ["willoverman", "americana", "folk"]


def get_raw_members_data(max_size, items_per_batch=1000):
    """
    ---args---
    batch_size: batch size for pagination (max is 1000)
    offset: the starting index for a batch

    ---returns---
    all_members_data: raw json data containing lots of attributes about each member in the list


    """
    batch_size = items_per_batch
    offset = 0

    all_members_data = []
    while offset < max_size:
        try:
            response = client.lists.get_list_members_info(
                list_id,
                count=batch_size,
                offset=offset,
            )
            all_members_data.extend(response["members"])
            if len(response["members"]) < batch_size:
                break
            offset += batch_size

        except ApiClientError as error:
            logging.error(error.text)

    logging.info(f"TOTAL ITEMS: {len(all_members_data)}")

    return all_members_data


def clean_data(all_members_data):
    """
    ---args---
    all_members_data: the raw data returned
    ---returns---
    cleaned_data: A list of objects containing members who have tags.
    Format is {id:id, tags:[list_of_current_tags]}
    """

    cleaned_data = []

    for member in all_members_data:
        if len(member["tags"]):
            list_of_current_tags = []
            for tag in member["tags"]:
                list_of_current_tags.append(tag["name"])
            cleaned_data.append({"id": member["id"], "tags": list_of_current_tags})

    return cleaned_data


def update_tags(member, old_tags=OLD_TAGS, new_tags=NEW_TAGS):
    """
    ---args---
    old_tags: the tags (strings) to be replaced
    new_tags: the tags to be added if any of the old_tags are removed

    tags_to_remove: a dict of old_tags with the proper format for the update_list_member_tags API call
    tags_to_add: a dict of new_tags with the proper format for the update_list_member_tags API call
    removed_tags = a list of removed tags for logging

    """

    tags_to_remove = [{"name": tag, "status": "inactive"} for tag in old_tags]
    tags_to_add = [{"name": tag, "status": "active"} for tag in new_tags]

    member_id = member["id"]
    removed_tags = []

    for otag in old_tags:
        if otag in member["tags"]:
            removed_tags.append(otag)

    if len(removed_tags):
        try:
            client.lists.update_list_member_tags(
                list_id, member_id, {"tags": tags_to_remove + tags_to_add}
            )
            logging.info(f"member ID: {member_id}, no changes")
            logging.info(f"removed tags: {removed_tags}")
            logging.info(f"added tags: {new_tags}\n")
        except ApiClientError as error:
            print("Error: {}".format(error.text))

    # else:
    #     logging.info(f"member ID: {member_id}, No changes!")


if __name__ == "__main__":
    raw_members_dict = get_raw_members_data(10000)
    cleaned_data = clean_data(raw_members_dict)
    for member in cleaned_data:
        update_tags(member)
