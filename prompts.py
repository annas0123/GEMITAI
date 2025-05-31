# prompts.py

# Structure: Dictionary where keys are category names
# Values are lists of dictionaries, each representing a prompt with 'title' and 'prompt_text'

PROMPT_CATEGORIES = {
    "Summarization": [
        {
            "title": "Summarize key points",
            "prompt_text": "Summarize the key points of the following text concisely:"
        },
        {
            "title": "Explain like I'm 5",
            "prompt_text": "Explain the following concept as if you were talking to a 5-year-old:"
        },
        {
            "title": "Extract action items",
            "prompt_text": "Extract all action items mentioned in the following text:"
        }
    ],
    "Creative Writing": [
        {
            "title": "Write a short story opening",
            "prompt_text": "Write the opening paragraph for a fantasy short story about a reluctant hero."
        },
        {
            "title": "Generate blog post ideas",
            "prompt_text": "Generate 5 blog post ideas about the future of renewable energy."
        },
        {
            "title": "Describe a scene",
            "prompt_text": "Write a short, vivid description of a bustling marketplace at dawn."
        }
    ],
    "Code Assistance": [
        {
            "title": "Explain Python code",
            "prompt_text": "Explain what the following Python code does:\n```python\n{code_here}\n```"
        },
        {
            "title": "Find bugs in Javascript",
            "prompt_text": "Review the following Javascript code for potential bugs:\n```javascript\n{code_here}\n```"
        }
    ],
    "Influencers": [
        {
            "title": "Engagement, niche, audience, criteria",
            "prompt_text": "Itemize the key criteria for selecting micro-influencers, such as engagement rates, niche expertise, and audience demographics."
        },
        {
            "title": "Micro-influencers, partnerships, mutually beneficial",
            "prompt_text": "Plan a strategy for reaching out to micro-influencers and establishing partnerships that are mutually beneficial."
        }
    ],
    "Youtube": [
        {
            "title": "Optimizing Video Titles for YouTube Search",
            "prompt_text": "What are the best practices for optimizing video titles for YouTube search?"
        },
        {
            "title": "Growing a YouTube Subscriber Base",
            "prompt_text": "What are some strategies for building a large and engaged YouTube subscriber base?"
        }
    ],
     "Video": [
        {
            "title": "Analyze the video ",
            "prompt_text": "\nPlease provide a detailed analysis of the video , including . \n   5 small Title:  \n    Description: 20 hashtags  \n   20 Tags:  \n  "
        },
        {
            "title": "Growing a YouTube Subscriber Base",
            "prompt_text": "What are some strategies for building a large and engaged YouTube subscriber base?"
        }
    ],
    "Twitter": [
        {
            "title": "Twitter following growth strategies",
            "prompt_text": "I want to find all content I have created (including but not limited to: documents, notes, articles, social media posts, saved links, emails, presentations, etc.) that is relevant to the topic of increasing my Twitter following and reaching a larger audience.\n\nSpecifically, I'm looking for content that addresses:\n\n*   **Strategies for gaining more followers on Twitter:** This includes techniques like follower targeting, content optimization, engagement tactics, and leveraging trends.\n*   **Methods for improving Twitter reach and visibility:** This includes strategies like hashtag research, timing of posts, content promotion, and optimizing Twitter profiles for discoverability.\n*   **Tactics for creating engaging and valuable Twitter content:** This includes content formats, voice and tone, community building, and providing value to the audience.\n*   **Tools and resources for Twitter growth:** This includes automation tools, analytics platforms, and educational resources.\n*   **Examples of successful Twitter growth strategies:** This includes case studies, examples of influential accounts, and lessons learned from successful campaigns.\n*   **Best practices for Twitter marketing and advertising:** This includes paid advertising strategies, targeting options, and measuring ROI.\n*   **Content related to my personal experiences and results with Twitter growth strategies.**\n\nPlease search through all my files, notes, accounts, and communications and return any items that are relevant to these topics.\n\nIf you have a specific query or area of focus within Twitter growth, please add it here: []"
        },
        {
            "title": "Twitter advanced search followers",
            "prompt_text": "Find all your documents, notes, articles, bookmarks, social media posts, emails, and any other saved information related to:\n\n*   **Twitter's Advanced Search Features:** Specifically, how to use the various filters and operators available (e.g., keywords, hashtags, date ranges, location, language, sentiment) to narrow down search results.\n*   **Finding Potential Followers on Twitter:** Strategies for identifying users who are likely to be interested in your content, product, or services.\n*   **Engaging with Potential Followers:** Best practices for interacting with users you've found through advanced search, including crafting compelling tweets, participating in relevant conversations, and building relationships.\n\nPlease include anything you've saved about:\n\n*   Specific advanced search operators (e.g., `from:`, `to:`, `near:`, `-keyword`) and their use cases.\n*   Examples of successful search queries you've used or seen.\n*   Tools or techniques you've used to analyze Twitter search results.\n*   Tips for personalizing your engagement approach based on the user's profile and interests.\n*   Case studies or articles about successful follower acquisition strategies using Twitter advanced search.\n*   Methods for tracking the results of your engagement efforts.\n\nIf you have a specific question or area you'd like to focus on within this topic, please add it here: [ ]"
        },
        {
            "title": "Optimize Twitter profile growth.",
            "prompt_text": "I want to find *all* available information, resources, and guides related to **optimizing a Twitter profile to attract more followers.** This includes (but is not limited to):\n\n*   **Profile Picture & Header Optimization:** Best image sizes, branding considerations, visual appeal strategies.\n*   **Bio Optimization:** Effective keyword usage, compelling value proposition, clear call to action.\n*   **Username Optimization:** Memorability, relevance, and searchability.\n*   **Content Strategy for Profile Growth:** Types of content that attract followers, posting frequency, engagement tactics.\n*   **Using Twitter Features for Growth:** Lists, Moments, Twitter Spaces.\n*   **Analyzing Profile Performance:** Using Twitter Analytics to track progress and identify areas for improvement.\n*   **Examples of successful Twitter profiles** (in various niches) and the strategies they employ.\n*   **Common mistakes to avoid** when optimizing a Twitter profile.\n*   **Tools and services** that can aid in profile optimization and growth.\n*   **Algorithm Changes**: How recent Twitter algorithm updates impact profile visibility and follower growth.\n*   **Paid Advertising:** Using Twitter Ads to promote your profile and attract followers (if applicable).\n\nPlease provide links, articles, tutorials, forum discussions, videos, and any other relevant resources.  Also, include both beginner-friendly and advanced techniques.\n\nIf you have a more specific question about optimizing your Twitter profile, you can ask it here: **[]**"
        }
    ],
    "Image Generation": [
        {
            "title": "Coloring book",
            "prompt_text": "Make a sketching of [] . i want to make a coloring book for kids, white and black, black thin border."
        },
        {
            "title": "Portrait image",
            "prompt_text": "Generate a professional portrait of a person with a neutral background, good lighting, and natural pose. The image should look like a high-quality headshot."
        },
        {
            "title": "Fantasy creature",
            "prompt_text": "Create an image of a mythical dragon with iridescent scales, sitting on a treasure hoard in a cave. The lighting should create a magical atmosphere with glowing elements."
        },
        {
            "title": "Product visualization",
            "prompt_text": "Generate a photorealistic image of a sleek, modern smartphone on a minimalist desk setup with soft lighting and shallow depth of field."
        },
        {
            "title": "Abstract art",
            "prompt_text": "Create an abstract digital artwork with fluid shapes, vibrant colors, and dynamic composition. The style should be modern and visually striking."
        }
    ],
    "Audio": [
        {
            "title": "Transcribe audio",
            "prompt_text": "Please transcribe this audio file as accurately as possible, including any background noises or unclear sections (marked with [inaudible])."
        },
        {
            "title": "Identify speakers",
            "prompt_text": "Please transcribe this conversation and identify different speakers as Speaker 1, Speaker 2, etc."
        },
        {
            "title": "Summarize audio content",
            "prompt_text": "Listen to this audio file and provide a concise summary of the main points discussed."
        },
        {
            "title": "Extract music information",
            "prompt_text": "Analyze this music track and identify the genre, instruments used, tempo, and overall mood."
        },
        {
            "title": "Analyze speech emotions",
            "prompt_text": "Listen to this speech and analyze the emotional tone and changes throughout the delivery."
        }
    ],
    "Aa default": [
       
    ],
    "PDF Analysis": [
        {
            "title": "Summarize document",
            "prompt_text": "Please provide a concise summary of this PDF document, highlighting the key points and main conclusions."
        },
        {
            "title": "Extract data tables",
            "prompt_text": "Identify and extract all data tables from this PDF document, presenting them in a well-structured format."
        },
        {
            "title": "Find key facts",
            "prompt_text": "List the 10 most important facts or statistics presented in this PDF document."
        },
        {
            "title": "Compare to industry standards",
            "prompt_text": "Analyze how the information in this document compares to current industry standards and best practices."
        },
        {
            "title": "Explain technical concepts",
            "prompt_text": "Explain the technical concepts presented in this PDF in simpler terms that a non-specialist could understand."
        }
    ],
    "Excel Analysis": [
        {
            "title": "Summarize dataset",
            "prompt_text": "Provide a comprehensive summary of this Excel dataset, including key metrics, patterns, and notable insights."
        },
        {
            "title": "Identify trends",
            "prompt_text": "Analyze this Excel data to identify significant trends, outliers, and patterns that might be valuable for decision-making."
        },
        {
            "title": "Suggest visualizations",
            "prompt_text": "Based on this Excel data, what visualization types would be most effective for presenting the key insights? Explain your reasoning."
        },
        {
            "title": "Data quality assessment",
            "prompt_text": "Evaluate the quality of this Excel dataset by checking for inconsistencies, missing values, outliers, and potential errors."
        },
        {
            "title": "Business recommendations",
            "prompt_text": "Based on this Excel data, what are the top 3-5 actionable business recommendations you would make?"
        }
    ],
    "Excel Row Processing": [
        {
            "title": "Row-by-row analysis",
            "prompt_text": "For each row in this Excel dataset, provide a detailed analysis of the information and its significance."
        },
        {
            "title": "Generate descriptions",
            "prompt_text": "Create a detailed description for each row in this Excel file, highlighting the key attributes and their relationships."
        },
        {
            "title": "Categorize entries",
            "prompt_text": "For each row, determine the most appropriate category or classification based on the provided attributes."
        },
        {
            "title": "Priority scoring",
            "prompt_text": "Assign a priority score (1-10) to each row based on the following criteria: [specify criteria here]"
        },
        {
            "title": "Generate action items",
            "prompt_text": "For each row, create a specific action item or next step based on the information provided."
        }
    ]
}

# You can add a function to easily retrieve this data if needed,
# but direct import is fine for now.
# def get_prompts():
#     return PROMPT_CATEGORIES