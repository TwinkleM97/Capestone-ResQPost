RESQPOST/
├── backend/
│   ├── app.py                 # Flask main application
│   ├── models.py              # SQLAlchemy models
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Backend Docker configuration
│   ├── .env.example          # Environment variables template
│   └── venv/                 # Python virtual environment
├── frontend/
│   ├── public/
│   │   ├── index.html        # Main HTML template
│   │   └── favicon.ico       # App icon
│   ├── src/
│   │   ├── components/
│   │   │   ├── AlertDetail.js    # Alert details page
│   │   │   ├── AlertForm.js      # Submit alert form
│   │   │   ├── AlertList.js      # List all alerts
│   │   │   ├── MapView.js        # Map view with pins
│   │   │   └── Home.js           # Landing page
│   │   ├── App.js            # Main React component
│   │   ├── index.js          # React entry point
│   │   └── App.css           # Global styles
│   ├── package.json          # NPM dependencies
│   ├── package-lock.json     # NPM lock file
│   └── Dockerfile           # Frontend Docker configuration
├── docker-compose.yml        # Multi-container setup
├── terraform/               # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── .github/
│   └── workflows/
│       └── ci-cd.yml        # GitHub Actions pipeline
└── README.md               # Project documentation