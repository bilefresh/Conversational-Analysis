"""
Created by Bilesanmi Faruk
"""

from collections import Counter
import re
import operator
import io
import sys
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl
from dateutil import parser
import emoji
import pandas as pd

# pylint: disable=invalid-name, W0603, W0621, W0622, W0612, W0703,  R0903

def replace_bad_character(line):
    """
    Removing the bad characters
    """
    return line.strip().replace(u"\u202a", "").replace(u"\u200e", "")\
        .replace(u"\u202c", "").replace(u"\xa0", " ")


filepath = input("Please input chat filepath: ")

try:
    with io.open(filepath, "r", encoding="utf-8") as file:
        content = [replace_bad_character(l) for l in file.readlines()]

except IOError as e:
    print(
        "File \"" +
        filepath +
        "\" not found. Please recheck your file location")
    sys.exit()

common_words = []
cw_filepath = ""

cw_option = "Please select common word file or leave it blank to escape: \n\
    1: English (en_cw.py)\n\
    2: Custom file\n\
    3: Skip common word\n"

cw = input(cw_option)

if cw == "1":
    cw_filepath = "en_cw"
elif cw == "2":
    cw_filepath = input("Please input your common word filepath: ")

if len(cw_filepath) > 0:
    try:
        common_words = __import__(
            cw_filepath,
            globals(),
            locals(),
            [common_words]).common_words
    except BaseException:
        print("Error getting common word file location")
        sys.exit()
else:
    print("You skipped common word.")

class bcolors:
    """
    Defining Colors
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


chat_of_members = {}
member_chat = {"member": [], "chat_count": []}
attachments = {}
refered_web = {"domain": [], "d_count": []}
popular_words = {}
chat_words = ""
emojis = {"emj_char": [], "char_count": []}
heat_map = {
    "day": [],
    "hour": [],
    "chat_count": []
}
deleted_message = 0
pure_chat = ""
total_chat = 0

"""
Starting line mean a line that started with date time.
Because there are multiline chat. I called it following line.
A starting line must be classified before it's data being extracted.
"""


def is_starting_line(line):
    """
    Extracting the starting the line, the date
    """
    pattern = r"""
        (\[?)       #Zero or one open square bracket '['
        (((\d{1,2})   #1 to 2 digit date
        (/|-)       #'/' or '-' separator
        (\d{1,2})   #1 to 2 digit month
        (/|-)       #'/' or '-' separator
        (\d{2,4}))   #2 to 4 digit of year
        (,?\s)      #Zero or one comma ',' and single space
        ((\d{1,2})  #1 to 2 digit of hour
        (:|\.)      #Colon ':' or dot '.' separator
        (\d{2})     #2 digit of minute
        (\.|:)?     #Zero or one of dot '.' or colon ':'
        (\d{2})?    #Zero or one of 2 digits of second
        (\s[AP]M)?))  #Zero or one of ('space', 'A' or 'P', and 'M'
        (\]?\s-?\s?\s?)#Zero or one close square bracket ']', Zero or one (space and '-'), zero or one space
        (.+)        #One or more character of chat member phone number or contact name
    """

    return re.match(re.compile(pattern, re.VERBOSE), line)


def is_chat(body):
    """
    Created by Bilesanmi Faruk
    """
    pattern = r"""
            ([^:]+)#Chat member
            (:)   #Colon separator
            (.+)  #One or more charachter of message content
    """

    return re.match(re.compile(pattern, re.VERBOSE), body)



##Classify attachment
##Note: in Android, there is no proper description whether it's a image,
##video, audio, gif, or sticker.



def contains_attachment(body):
    """
    Extracting the attachments
    """
    pattern_attachment = [
        ".*<Media omitted>$",  # English version of android attachment
        r".+\.vcf \(file\sattached\)$",
        ".*image omitted$",
        ".*video omitted$",
        ".*document omitted$",
        ".*Contact card omitted$",
        ".*audio omitted$",
        ".*GIF omitted$",
        ".*sticker omitted$"
    ]

    for p in pattern_attachment:
        match = re.match(p, body)
        if match:
            return body
    return None

#Event means logs of chat activity e.g member left, member added, removed, etc.

def is_event(body):
    """
    Extracting the events
    """
    pattern_event = [
        r"Messages to this group are now secured with end-to-end encryption\.$",
        r".+\screated this group$",
        r".+\sleft$",
        r".+\sadded\s.+",
        r".+\sremoved\s.+",
        ".*You joined using this group's invite links$",
        r".+'s security code changed\.$",
        r".*changed their phone number to a new number. Tap to message or add the new number\.$"]

    for p in pattern_event:
        match = re.match(p, body)
        if match:
            return match
    return None

#Deleted message

def is_deleted(body):
    """
    Extracting the deleted texts
    """
    p = [
        r".*This message was deleted\.$"
    ]

    for p in p:
        match = re.match(p, body)
        if match:
            return body
    return None


#EXTRACT TIMESTAMP

def extract_timestamp(time_string):
    """
    Extrcating the time
    """
    return parser.parse(time_string)

#Check if chat contains a url

def extract_url(body):
    """
    Extracting the links
    """
    pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"

    return re.findall(pattern, body)


def get_domain(str):
    """
    Get the dmain names
    """
    domain = str.replace("http://", '')
    domain = domain.replace("https://", '')
    domain = domain.split("/")
    return domain[0]

#EMOJI

def extract_emojis(string):
    """
    Extractin the emojis
    """
    emj = []
    for c in string:
        if c in emoji.UNICODE_EMOJI:
            emj.append(c)

    if len(emj) > 0:
        increment_emoji_count(emj)

    return emj


#Count top words

def get_words(msg):
    """
    Getting the words
    """
    # remove non alpha content
    regex = re.sub(r"[^a-z\s]+", "", msg.lower())
    regex = re.sub(r'[^\x00-\x7f]', r'', regex)
    words = regex.split(" ")

    for x in words:
        if x:
            rank_word(x)

    return words


def rank_word(word):
    """
    Ranking the words
    """
    if word not in common_words:
        popular_words[word] = popular_words.get(word, 0) + 1
        global chat_words
        chat_words += " {0}".format(word)

    return word

#Rank the 'Most Active user'

def increment_chat_count(member):
    """
    Counting the number of chats
    """
    member_chat["member"].append(member)
    member_chat["chat_count"].append(1)
    global total_chat
    total_chat += 1

    return member

def increment_attachment_count(message):
    """
    Counting the number of attachments
    """
    if "image omitted" in message:
        attachments["image"] = attachments.get("image", 0) + 1
        return

    if "video omitted" in message:
        attachments["video"] = attachments.get("video", 0) + 1
        return

    if "audio omitted" in message:
        attachments["audio"] = attachments.get("audio", 0) + 1
        return

    if "document omitted" in message:
        attachments["document"] = attachments.get("document", 0) + 1
        return

    if "Contact card omitted" in message or ".vcf" in message:
        attachments["contact"] = attachments.get("contact", 0) + 1
        return

    if "sticker omitted" in message:
        attachments["sticker"] = attachments.get("sticker", 0) + 1
        return

    # Unknown attachment
    attachments["unknown"] = attachments.get("unknown", 0) + 1


def increment_link_count(urls):
    """
    Counting the number of links
    """
    for url in urls:
        increment_domain_count(get_domain(url))

    return len(urls)


def increment_domain_count(domain):
    """
    Counting the number of domains
    """
    refered_web["domain"].append(domain)
    refered_web["d_count"].append(1)


def increment_emoji_count(char_list):
    """
    Counting the number of emojis
    """
    groups = Counter(char_list)
    for c in groups.items():
        emojis["emj_char"].append(c[0])
        emojis["char_count"].append(c[1])


def increment_heatmap(dt):
    """
    Heatmap
    """
    heat_map["day"].append(dt.strftime("%A"))
    heat_map["hour"].append(dt.strftime("%H"))
    heat_map["chat_count"].append(1)


def increment_deleted():
    """
    Counting the Deleted Messages
    """
    global deleted_message
    deleted_message += 1

def parse_line(line):
    """
    Parsing the line
    """
    prefix = ""
    is_starting = is_starting_line(line)

    if is_starting:
        # Check wether the starting line is a chat or an event
        body = is_starting.group(18)
        chat = is_chat(body)
        dt = extract_timestamp(is_starting.group(2).replace(".", ":"))
        increment_heatmap(dt)

        if chat:
            has_attachment = contains_attachment(chat.group(3))
            increment_chat_count(chat.group(1))
            message_body = chat.group(3)
            # print(chat.groups())

            if has_attachment:
                prefix = "@@@"
                increment_attachment_count(has_attachment)

            else:
                if is_deleted(message_body):
                    increment_deleted()
                else:
                    prefix = "+++"

                    #URL & Domain
                    urls = extract_url(message_body)
                    if urls:
                        increment_link_count(urls)

                    # Emoji
                    emjs = extract_emojis(message_body)

                    # Word Count
                    get_words(message_body)

        elif is_event(body):
            prefix = "***"

    else:
        prefix = "|||"

        #URL & Domain
        urls = extract_url(line)
        if urls:
            increment_link_count(urls)

        # Emoji
        emjs = extract_emojis(line)

        # Word Count & Wordcloud
        get_words(line)


print("Extracting data. Please wait....")

for line in content:
    parse_line(line)

print("Generating dataframe...")
chat_per_member = (pd.DataFrame(member_chat)\
                     .groupby(["member"])\
                     .sum()\
                     .sort_values(by=['chat_count'], ascending=False))
popular_words_df = sorted(
    popular_words.items(),
    key=operator.itemgetter(1),
    reverse=True)
domains = (pd.DataFrame(refered_web)
           .groupby(["domain"])
           .sum()
           .sort_values(by=['d_count'], ascending=False))
emojis_df = (pd.DataFrame(emojis)
             .groupby(["emj_char"])
             .sum()
             .sort_values(by=['char_count'], ascending=False))
top_repeated_emoji = (pd.DataFrame(emojis)
                      .sort_values(by=['char_count'], ascending=False))
heatmap_df = pd.DataFrame(heat_map)
grouped_heatmap = heatmap_df.groupby(["day", "hour"]).sum().sort_values(by=[
    "chat_count"], ascending=False)
pivoted_heatmap = pd.pivot_table(
    grouped_heatmap,
    values='chat_count',
    index=['day'],
    columns=['hour'])

print("Generating plot...")

#Top Members

top_member = chat_per_member.head(20)
if not top_member.empty:
    sns.set()
    member_plot = top_member.plot(
        kind='bar',
        legend=None,
        title="Top 20 active members",
        figsize=(
            18,
            6),
        color="purple")
    member_plot.set_xlabel("Member (phone number/contact name)")
    member_plot.set_ylabel("Chat Count")
    for i, v in enumerate(top_member["chat_count"]):
        member_plot.text(i - .15, v + 3, v, color="#004d40")
else:
    print("This chat has no member")

#Heatmap

heatmap_df = pd.DataFrame(heat_map)
if not heatmap_df.empty:
    grouped_heatmap = heatmap_df.groupby(["day", "hour"]).sum(
    ).sort_values(by=["chat_count"], ascending=False)
    pivoted_heatmap = pd.pivot_table(
        grouped_heatmap,
        values='chat_count',
        index=['day'],
        columns=['hour'])
    plt.figure(figsize=(16, 5))
    sns.heatmap(pivoted_heatmap,
                annot=True,
                fmt=".0f",
                linewidths=.2,
                cmap="YlGnBu",
                cbar=False
                )

    plt.show()
else:
    print("This chat does not contain any datetime")

#Pie chart of the attachments sent

s_attachments = sorted(
    attachments.items(),
    key=operator.itemgetter(1),
    reverse=True)
if s_attachments:
    at_labels = [x[0].title() + " " + str(x[1]) for x in s_attachments]
    at_explode = tuple([0 + i * 0.1 for i in range(len(s_attachments))])
    at_sizes = [x[1] for x in s_attachments]
    at_colors = [
        "#FF6D00",
        "#64DD17",
        "#00B8D4",
        "#304FFE",
        "#AA00FF",
        "#d50000",
        "#546E7A",
        "#dddddd"]
    at_pie = plt.pie(at_sizes,
                     autopct='%1.1f%%',
                     explode=at_explode,
                     pctdistance=1.2,
                     colors=at_colors,
                     startangle=160,
                     radius=1.3,
                     wedgeprops={'linewidth': 2, 'edgecolor': 'white'},
                     )

    at_centre_circle = plt.Circle(
        (0, 0), 0.85, color='white', fc='white', linewidth=1.25)
    at_fig = plt.gcf()
    at_fig.gca().add_artist(at_centre_circle)

    plt.legend(
        loc='upper left',
        labels=at_labels,
        prop={'size': 11},
        bbox_to_anchor=(1, 1)
    )
    at_axis = plt.axis('equal')

    plt.show()
else:
    print("This chat contains no attachment.")

#Top Website

top_web = domains.head(20).sort_values("d_count")
if not top_web.empty:
    mpl.rc('font', **{'sans-serif': 'arial', 'family': 'sans-serif'})
    web_plot = top_web.plot(
        kind='barh',
        legend=None,
        title="Top 20 mentioned domain",
        figsize=(
            20,
            10),
        color="#1de9b6")
    web_plot.set_xlabel("Mention Count")
    for i, v in enumerate(top_web["d_count"]):
        web_plot.text(1, i - .15, v, color="purple")
else:
    print("This chat not contains any link")

#Output

print("\n=======================================\n")
print("#Total Chat: {0}".format(total_chat))
print("#Deleted Message: {0}".format(deleted_message))
print("#Total Attachment: {0}".format(sum([x[1] for x in s_attachments])))
for a in s_attachments:
    print("  - : {0}".format(a))


print("\n#Top 20 Member")
print("-----------------")
print(top_member)


print("\n#Top 20 Words")
print("-----------------")
for k, v in enumerate(popular_words_df):
    if k < 20:
        print(v)
    else:
        break

print("\n#Top 20 Emoji")
print("-----------------")
print(emojis_df.head(20))

print("\n#Top 20 Mentioned Website")
print("-----------------")
print(top_web.sort_values("d_count", ascending=False))
