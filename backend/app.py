from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from database import db, users_collection, progress_collection, rehab_centres_collection
from models import User,LoginUser
import bcrypt
from jose import jwt   
from datetime import datetime,timedelta
from math import radians,sin,cos,sqrt,atan2
from urllib.parse import urlencode,quote 
from urllib.request import Request, urlopen
import json
import requests
app = FastAPI()
SECRET_KEY = "nasha-mukti-secret-key"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60
def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    token = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hopebridge-rqf6.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



def distance_in_km(latitude_a, longitude_a, latitude_b, longitude_b):
    """Return the straight-line distance between two coordinates in kilometres."""
    earth_radius = 6371
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    calculation = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(longitude_delta / 2) ** 2
    )
    return earth_radius * 2 * atan2(sqrt(calculation), sqrt(1 - calculation))


def format_address(tags):
    address_parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city") or tags.get("addr:district"),
        tags.get("addr:state"),
    ]
    return ", ".join(part for part in address_parts if part) or "Address not listed"
# =========================
# LOCATION SEARCH
# =========================

@app.get("/search-location")
def search_location(q: str = Query(..., min_length=2)):
    """
    Convert a typed city, area or landmark into coordinates
    using OpenStreetMap Nominatim.
    """

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": q,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "Nasha-Mukti-CollegeProject/1.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=503,
                detail="Location search service is unavailable."
            )

        results = response.json()

        if not results:
            raise HTTPException(
                status_code=404,
                detail="Location not found."
            )

        location = results[0]

        return {
            "display_name": location["display_name"],
            "latitude": float(location["lat"]),
            "longitude": float(location["lon"])
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Location search failed:", repr(error))

        raise HTTPException(
            status_code=503,
            detail="Unable to search for this location right now."
        )


# =========================
# NEARBY REHABILITATION CENTRES
# =========================

@app.get("/rehabilitation-centres")
def rehabilitation_centres(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: int = Query(25, ge=5, le=50)
):
    """
    Find rehabilitation centres stored in MongoDB
    that are within the requested radius.
    """

    centres = []

    records = list(rehab_centres_collection.find({}))

    for record in records:

        if "latitude" not in record or "longitude" not in record:
            continue

        centre_latitude = float(record["latitude"])
        centre_longitude = float(record["longitude"])

        distance = distance_in_km(
            latitude,
            longitude,
            centre_latitude,
            centre_longitude
        )

        if distance > radius:
            continue

        centres.append({
            "name": record.get(
                "name",
                "Rehabilitation Centre"
            ),
            "address": record.get(
                "address",
                "Address not listed"
            ),
            "phone": record.get(
                "phone",
                "Phone not listed"
            ),
            "website": record.get(
                "website"
            ),
            "latitude": centre_latitude,
            "longitude": centre_longitude,
            "distance": round(distance, 1),
            "source": record.get(
                "source",
                "Nasha Mukti Database"
            )
        })

    centres.sort(
        key=lambda centre: centre["distance"]
    )

    return {
        "centres": centres[:20],
        "radius": radius
    }

@app.get("/database-test")
def database_test():
    try:
        db.command("ping")

        return {
            "message": "MongoDB connected successfully"
        }

    except Exception as e:
        return {
            "message": "MongoDB connection failed",
            "error": str(e)
        }
@app.post("/register")
def register(user: User):

    hashed_password = bcrypt.hashpw(
        user.password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user_data = {
        "name": user.name,
        "email": user.email,
        "password": hashed_password.decode("utf-8")
    }

    result = users_collection.insert_one(user_data)

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }
@app.post("/login")
def login(user: LoginUser):

    existing_user = users_collection.find_one({
        "email": user.email
    })

    if existing_user is None:
        return {
            "message": "Invalid email or password"
        }

    password_match = bcrypt.checkpw(
        user.password.encode("utf-8"),
        existing_user["password"].encode("utf-8")
    )

    if not password_match:
        return {
            "message": "Invalid email or password"
        }

    token = create_access_token({
    "email": existing_user["email"]
})

    return {
    "message": "Login successful",
    "name": existing_user["name"],
    "access_token": token
}
def get_current_user(authorization: str):

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email = payload.get("email")

        if email is None:
            return None

        user = users_collection.find_one({
            "email": email
        })

        return user

    except Exception:
        return None
@app.post("/progress")
def save_progress(authorization: str = Header(None)):

    if authorization is None:
        return {
            "message": "Authorization token required"
        }

    user = get_current_user(authorization)

    if user is None:
        return {
            "message": "Invalid or expired token"
        }

    today = datetime.utcnow().strftime("%Y-%m-%d")

    existing_progress = progress_collection.find_one({
        "user_email": user["email"],
        "date": today
    })

    if existing_progress is not None:
        return {
            "message": "Today's progress is already recorded"
        }

    progress_data = {
        "user_email": user["email"],
        "user_name": user["name"],
        "status": "completed",
        "date": today
    }

    progress_collection.insert_one(progress_data)

    return {
        "message": "Today's progress saved successfully"
    }
@app.get("/progress")
def get_progress(authorization: str = Header(None)):

    if authorization is None:
        return {
            "message": "Authorization token required"
        }

    user = get_current_user(authorization)

    if user is None:
        return {
            "message": "Invalid or expired token"
        }

    records = list(
        progress_collection.find(
            {"user_email": user["email"]}
        )
    )

    progress_list = []

    for record in records:

     record_date = record["date"]

     if isinstance(record_date, str):
        formatted_date = record_date
     else:
        formatted_date = record_date.strftime("%Y-%m-%d")

     progress_list.append({
        "date": formatted_date,
        "status": record["status"]
    })

    return {
        "user_name": user["name"],
        "total_days": len(progress_list),
        "progress": progress_list
    }
@app.get("/awareness")
def get_awareness():

    return {
        "title": "Drug and Alcohol Awareness",
        "topics": [
            {
                "name": "Drug Addiction",
                "description": "Drug addiction can affect physical health, mental health, relationships and daily life."
            },
            {
                "name": "Alcohol Addiction",
                "description": "Excessive alcohol use can lead to dependence and can affect the liver, brain, heart and relationships."
            },
            {
                "name": "Warning Signs",
                "description": "Changes in behaviour, loss of control, withdrawal from family and problems at school or work can be warning signs."
            },
            {
                "name": "Seeking Help",
                "description": "People struggling with addiction can seek support from healthcare professionals, counsellors, family and trusted support services."
            }
        ]
    }
@app.get("/recovery-tips")
def get_recovery_tips():

    return {
        "title": "Recovery Tips",
        "tips": [
            {
                "title": "Stay Connected",
                "description": "Stay connected with supportive family members, friends or trusted people."
            },
            {
                "title": "Avoid Triggers",
                "description": "Identify situations, places or people that may encourage substance use and try to avoid them."
            },
            {
                "title": "Maintain a Healthy Routine",
                "description": "Regular sleep, nutritious food and physical activity can support a healthy recovery routine."
            },
            {
                "title": "Seek Professional Support",
                "description": "Counsellors, doctors and addiction-recovery professionals can provide appropriate guidance and support."
            }
        ]
    }
@app.get("/support")
def get_support():

    return {
        "title": "Government & Support Services",
        "information": [
            {
                "title": "🇮🇳 Nasha Mukt Bharat Abhiyaan",
                "description": "Nasha Mukt Bharat Abhiyaan is a Government of India initiative for awareness, prevention, treatment, rehabilitation and community support related to substance use."
            },
            {
                "title": "📞 National De-addiction Helpline",
                "description": "Call 14446 for drug de-addiction counselling and referral support."
            },
            {
                "title": "🏥 Rehabilitation & Treatment Services",
                "description": "Government-supported services include Integrated Rehabilitation Centres for Addicts (IRCAs), District De-Addiction Centres (DDACs), Outreach and Drop-in Centres (ODICs) and Addiction Treatment Facilities (ATFs)."
            },
            {
                "title": "👨‍👩‍👧 Family Support",
                "description": "Family members can also seek guidance and support through the national de-addiction helpline."
            }
        ],
        "helpline": "14446",
        "official_website": "https://nmba.dosje.gov.in/"
    }
@app.post("/self-assessment")
def self_assessment(answers: list[int]):

    score = sum(answers)

    if score <= 3:
        result = "Low Concern"
        message = "Your answers indicate a lower level of concern. Continue maintaining healthy habits and avoiding harmful substances."

    elif score <= 7:
        result = "Moderate Concern"
        message = "Your answers indicate some areas of concern. Consider talking with a trusted person or qualified professional."

    else:
        result = "High Concern"
        message = "Your answers indicate a higher level of concern. Consider seeking support from a qualified healthcare or de-addiction professional."

    return {
        "score": score,
        "result": result,
        "message": message
    }
# =========================
# SEARCH LOCATION
# =========================

@app.get("/search-location")
def search_location(q: str):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": q,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "NashaMukti-CollegeProject/1.0"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        return {
            "message": "Location search service is unavailable."
        }

    results = response.json()

    if not results:
        return {
            "message": "Location not found."
        }

    location = results[0]

    return {
        "display_name": location["display_name"],
        "latitude": float(location["lat"]),
        "longitude": float(location["lon"])
    }
@app.get("/test-overpass")
def test_overpass():

    url = "https://overpass-api.de/api/interpreter"

    query = """
    [out:json];
    node(18.5204,73.8567,18.5304,73.8667);
    out 1;
    """

    try:

        response = requests.post(
            url,
            data={"data": query},
            headers={
                "User-Agent": "Nasha-Mukti-CollegeProject/1.0"
            },
            timeout=30
        )

        return {
            "status_code": response.status_code,
            "response": response.text[:1000]
        }

    except Exception as error:

        return {
            "error": repr(error)
        }

@app.get("/test-rehab-query")
def test_rehab_query():

    url = "https://overpass-api.de/api/interpreter"

    query = """
           [out:json][timeout:20];

           (
           nwr(
            around:10000,
             18.5204,
             73.8567
                 )["name"~"rehab|rehabilitation|addiction|de.?addiction|muktangan|nasha|vyasan|recovery",i];
               );

            out center tags;
         """

    try:

        response = requests.post(
            url,
            data={"data": query},
            headers={
                "User-Agent": "Nasha-Mukti-CollegeProject/1.0"
            },
            timeout=30
        )

        return {
            "status_code": response.status_code,
            "elements": response.json().get("elements", [])
        }

    except Exception as error:

        return {
            "error": repr(error)
        }