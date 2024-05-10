# p2app/engine/main.py
#
# ICS 33 Spring 2024
# Project 2: Learning to Fly
#
# An object that represents the engine of the application.
#
# This is the outermost layer of the part of the program that you'll need to build,
# which means that YOU WILL DEFINITELY NEED TO MAKE CHANGES TO THIS FILE.

import sqlite3
from pathlib import Path
from p2app.events import *


class Engine:
    """An object that represents the application's engine, whose main role is to
    process events sent to it by the user interface, then generate events that are
    sent back to the user interface in response, allowing the user interface to be
    unaware of any details of how the engine is implemented.
    """

    def __init__(self):
        """Initializes the engine"""
        self.connection = None
        pass


    def process_event(self, event):
        """A generator function that processes one event sent from the user interface,
        yielding zero or more events in response."""

        # Handle database-related events
        if isinstance(event, OpenDatabaseEvent):
            yield from self.open_database(event.path())
        elif isinstance(event, CloseDatabaseEvent):
            yield from self.close_database()

        # Handle continent-related events
        elif isinstance(event, StartContinentSearchEvent):
            yield from self.search_continents(event.continent_code(), event.name())
        elif isinstance(event, LoadContinentEvent):
            yield from self.load_continent(event.continent_id())
        elif isinstance(event, SaveNewContinentEvent):
            yield from self.save_new_continent(event.continent())
        elif isinstance(event, SaveContinentEvent):
            yield from self.save_continent(event.continent())

            # Handling country-related events
        elif isinstance(event, StartCountrySearchEvent):
            yield from self.search_countries(event.country_code(), event.name())
        elif isinstance(event, LoadCountryEvent):
            yield from self.load_country(event.country_id())
        elif isinstance(event, SaveNewCountryEvent):
            yield from self.save_new_country(event.country())
        elif isinstance(event, SaveCountryEvent):
            yield from self.save_country(event.country())

        # Handle region-related events
        elif isinstance(event, StartRegionSearchEvent):
            yield from self.search_regions(event.region_code(), event.local_code(), event.name())
        elif isinstance(event, LoadRegionEvent):
            yield from self.load_region(event.region_id())
        elif isinstance(event, SaveNewRegionEvent):
            yield from self.save_new_region(event.region())
        elif isinstance(event, SaveRegionEvent):
            yield from self.save_region(event.region())

    def open_database(self, path = None):
        """Opens the database at the specified path"""
        try:
            if path:
                self.connection = sqlite3.connect(path)
            else:
                self.connection = sqlite3.connect(self.db_path)
            yield DatabaseOpenedEvent(self.db_path)
        except sqlite3.Error as e:
            yield DatabaseOpenFailedEvent(str(e))

    def close_database(self):
        """Closes the currently open database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            yield DatabaseClosedEvent()

    def search_continents(self, continent_code, name):
        """Searches for continents matching the given criteria"""
        if self.connection:
            cursor = self.connection.cursor()
            query = "SELECT * FROM continents WHERE 1=1"
            params = []

            if continent_code:
                query += " AND continent_code = ?"
                params.append(continent_code)

            if name:
                query += " AND name LIKE ?"
                params.append(f"%{name}%")

            cursor.execute(query, params)
            results = cursor.fetchall()

            for row in results:
                continent = Continent(row[0], row[1], row[2])
                yield ContinentSearchResultEvent(continent)

    def load_continent(self, continent_id):
        """Loads a continent from the database by its ID"""
        if self.connection:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM continents WHERE continent_id = ?", (continent_id,))
            row = cursor.fetchone()

            if row:
                continent = Continent(row[0], row[1], row[2])
                yield ContinentLoadedEvent(continent)
            else:
                yield ErrorEvent(f"Continent with ID {continent_id} not found")

    def save_new_continent(self, continent):
        """Saves a new continent to the database"""
        if self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "INSERT INTO continents (continent_code, name) VALUES (?, ?)",
                    (continent.continent_code, continent.name)
                )
                self.connection.commit()
                continent_id = cursor.lastrowid
                saved_continent = Continent(continent_id, continent.continent_code, continent.name)
                yield ContinentSavedEvent(saved_continent)
            except sqlite3.Error as e:
                yield SaveContinentFailedEvent(str(e))

    def save_continent(self, continent):
        """Saves an existing continent to the database"""
        if self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "UPDATE continents SET continent_code = ?, name = ? WHERE continent_id = ?",
                    (continent.continent_code, continent.name, continent.continent_id)
                )
                self.connection.commit()
                yield ContinentSavedEvent(continent)
            except sqlite3.Error as e:
                yield SaveContinentFailedEvent(str(e))

    def search_countries(self, country_code, name):
        """Searches for countries matching the given criteria"""
        if self.connection:
            cursor = self.connection.cursor()
            query = "SELECT * FROM country WHERE 1=1"
            params = []

            if country_code:
                query += " AND country_code = ?"
                params.append(country_code)

            if name:
                query += " AND name LIKE ?"
                params.append(f"%{name}%")

            cursor.execute(query, params)
            results = cursor.fetchall()

            for row in results:
                country = Country(row[0], row[1], row[2], row[3], row[4], row[5])
                yield CountrySearchResultEvent(country)

    def load_country(self, country_id):
        """Loads a country from the database by its ID"""
        if self.connection:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM country WHERE country_id = ?", (country_id,))
            row = cursor.fetchone()

            if row:
                country = Country(*row)
                yield CountryLoadedEvent(country)

            else:
                yield ErrorEvent(f"Country with ID {country_id} not found")

    def save_new_country(self, country):
        """Saves a new country into the database"""
        if self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO country (country_code, name, continent_id, wikipedia_link, keywords) VALUES (?, ?, ?, ?, ?)",
                (country.country_code, country.name, country.continent_id, country.wikipedia_link,
                 country.keywords))
            self.connection.commit()

            # Calling  to get the ID of the country we just inserted
            country_id = cursor.lastrowid

            # Loading the continent we just inserted (to get any default values provided by the database)
            yield from self.load_country(country_id)

    def save_country(self, country):
        """Saves the changes made to an existing country into the database"""
        if self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE country SET country_code = ?, name = ?, continent_id = ?, wikipedia_link = ?, keywords = ? WHERE country_id = ?",
                (country.country_code, country.name, country.continent_id, country.wikipedia_link,
                 country.keywords, country.country_id))
            self.connection.commit()

            # Reloading the country we just saved to make sure we have the latest data
            yield from self.load_country(country.country_id)

    def search_regions(self, region_code, local_code, name):
        """Searches for regions matching the given criteria"""
        if self.connection:
            cursor = self.connection.cursor()
            query = "SELECT * FROM regions WHERE 1=1"
            params = []

            if region_code:
                query += " AND region_code = ?"
                params.append(region_code)

            if local_code:
                query += " AND local_code = ?"
                params.append(local_code)

            if name:
                query += " AND name LIKE ?"
                params.append(f"%{name}%")

            try:
                cursor.execute(query, params)
                results = cursor.fetchall()

                for row in results:
                    region = Region(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
                    yield RegionSearchResultEvent(region)
            except sqlite3.Error as e:
                yield ErrorEvent(str(e))

    def load_region(self, region_id):
        """Loads a region from the database by its ID"""
        if self.connection:
            cursor = self.connection.cursor()
            try:
                cursor.execute("SELECT * FROM regions WHERE region_id = ?", (region_id,))
                row = cursor.fetchone()

                if row:
                    region = Region(*row)
                    yield RegionLoadedEvent(region)
                else:
                    yield ErrorEvent(f"Region with ID {region_id} not found")
            except sqlite3.Error as e:
                yield ErrorEvent(str(e))

    def save_new_region(self, region):
        """Saves a new region into the database"""
        if self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "INSERT INTO regions (region_code, local_code, name, continent_id, country_id, wikipedia_link, keywords) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (region.region_code, region.local_code, region.name, region.continent_id,
                     region.country_id,
                     region.wikipedia_link, region.keywords))
                self.connection.commit()

                # Get the ID of the newly inserted region
                region_id = cursor.lastrowid

                # Load the newly inserted region to get any default values
                yield from self.load_region(region_id)
            except sqlite3.Error as e:
                yield SaveRegionFailedEvent(str(e))

    def save_region(self, region):
        """Saves the changes made to an existing region into the database"""
        if self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "UPDATE regions SET region_code = ?, local_code = ?, name = ?, continent_id = ?, country_id = ?, wikipedia_link = ?, keywords = ? WHERE region_id = ?",
                    (region.region_code, region.local_code, region.name, region.continent_id,
                     region.country_id,
                     region.wikipedia_link, region.keywords, region.region_id))
                self.connection.commit()

                # Reloading the region we just saved to make sure we have the latest data
                yield from self.load_region(region.region_id)
            except sqlite3.Error as e:
                yield SaveRegionFailedEvent(str(e))
