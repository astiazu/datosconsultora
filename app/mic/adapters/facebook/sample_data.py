from datetime import datetime

facebook_post = {

    "post_id": "POST-001",

    "title": "¿Qué opinás del proyecto?",

    "comments": [

        {
            "comment_id": "1",
            "user_id": "100",
            "user_name": "José",
            "text": "Excelente iniciativa",
            "date": datetime.now()
        },

        {
            "comment_id": "2",
            "user_id": "101",
            "user_name": "María",
            "text": "No me convence",
            "date": datetime.now()
        },

        {
            "comment_id": "3",
            "user_id": "102",
            "user_name": "Pedro",
            "text": "Habrá que esperar...",
            "date": datetime.now()
        }

    ]
}