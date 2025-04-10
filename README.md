# Pronote App

A Python application to access Pronote data using the pronotepy API. Available as a web application.

## Features

- Login to Pronote (with ENT support)
- View homework
- View grades
- View timetable
- View periods

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/pronote-app.git
   cd pronote-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Web Application

Run the web application:
```
python pronote_web_app.py
```

Then open your browser and navigate to:
```
http://127.0.0.1:5000
```

The web application provides a modern, responsive interface with:
- Login screen with ENT support
- Dashboard with quick access to all features
- Homework view with filtering options
- Grades view with period selection
- Timetable view with date navigation
- Mobile-friendly design using Bootstrap

### Features

1. **Login System**
   - Support for direct Pronote login
   - Support for ENT authentication
   - Secure session management

2. **Homework Management**
   - View upcoming homework assignments
   - Filter by number of days ahead
   - See completion status

3. **Grade Tracking**
   - View grades for any period
   - See detailed grade information
   - Period selection dropdown

4. **Timetable Viewer**
   - View daily schedule
   - Navigate between days
   - See room and teacher information

## ENT Support

The application supports various ENTs (Espace Numérique de Travail) for authentication:
- ac_reunion
- ac_reims
- ac_orleans_tours
- ac_montpellier
- ac_lille
- ac_nancy_metz
- ac_nantes
- ac_bordeaux
- ac_toulouse
- ac_caen
- ac_rouen
- ac_poitiers
- ac_grenoble
- ac_lyon
- ac_clermont
- ac_dijon
- ac_besancon
- ac_strasbourg
- ac_creteil
- ac_versailles
- ac_paris

## Notes

- This application is for educational purposes only.
- Make sure you have the correct Pronote URL (it should point directly to the HTML file).
- The application will automatically refresh the session if it expires.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [pronotepy](https://github.com/bain3/pronotepy) - The Python API wrapper for Pronote