from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app
from app.models import db, User, Book, Listing, Review, Favorite, Transaction, Reservation, Photo, ImageFile
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
import secrets
from datetime import datetime
from supabase import create_client, Client  # Zorg ervoor dat 'Client' hier correct is geïmporteerd


main = Blueprint('main', __name__)

# Alle functies voor logged out pagina 
# Homepage for logged-out users
@main.route('/')
def index():
    available_listings = Listing.query.filter_by(status='Available').all()
    reserved_listings = Listing.query.filter_by(status='Reserved').all()
    sold_listings = Listing.query.filter_by(status='Sold').all()

    if current_user.is_authenticated:
        return render_template(
            'index_logged_in.html',
            available_listings=available_listings,
            reserved_listings=reserved_listings,
            sold_listings=sold_listings,
        )
    return render_template(
        'index_logged_out.html',
        available_listings=available_listings,
        sold_listings=sold_listings,
    )

# Registreren
@main.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone_number = request.form.get('phone_number')

        # Check if name or email already exists
        name_error = None
        email_error = None

        if User.query.filter_by(name=name).first():
            name_error = "Name is already taken. Please use another."
        if User.query.filter_by(email=email).first():
            email_error = "Email is already registered. Please use another."

        if name_error or email_error:
            # Render register.html with error messages
            return render_template('register.html', name_error=name_error, email_error=email_error)

        # If no errors, register the user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        new_user = User(name=name, email=email, password=hashed_password, phone_number=phone_number)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('main.login'))

    return render_template('register.html')

# Inloggen
@main.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Inloggen succesvol!", "success")
            return redirect(url_for('main.index'))
        else:
            flash("Foutieve inloggegevens", "danger")
    return render_template('login.html')

# Uitloggen
@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Succesvol uitgelogd!", "info")
    return redirect(url_for('main.index'))

# Alle functies ingelogde pagina 
# Configuratie voor bestandstoegang
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Supabase configuratie
SUPABASE_URL = 'https://hstybmdnkrtrsejimvei.supabase.co'  # Vervang dit met jouw project-URL
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhzdHlibWRua3J0cnNlamltdmVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI3MDY0OTYsImV4cCI6MjA0ODI4MjQ5Nn0.1rER1nDIrknL_oSz8wOtP2SEJ0oknktpL7HCF-IpsqI'  # Vervang dit met jouw anon-key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Controle of bestand is toegestaan
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Functie om bestanden te uploaden naar Supabase Storage
from werkzeug.utils import secure_filename

from werkzeug.utils import secure_filename
import os

def upload_image_to_supabase(file):
    try:
        filename = secure_filename(file.filename)  # Veilige bestandsnaam
        bucket_name = "foto"  # Bucketnaam in Supabase
        bucket_path = f"uploads/{filename}"  # Pad binnen de bucket

        # Tijdelijk bestand opslaan op de server
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)

        # Upload bestand naar Supabase vanuit het tijdelijke bestandspad
        with open(temp_path, "rb") as f:  # Open het bestand in leesmodus als bytes
            response = supabase.storage.from_(bucket_name).upload(bucket_path, f)

        # Controleer of upload succesvol is
        if response is None:
            print("Upload mislukt.")
            return None

        # Genereer de publieke URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(bucket_path)
        print(f"Public URL: {public_url}")

        # Verwijder tijdelijk bestand
        os.remove(temp_path)

        return public_url

    except Exception as e:
        print(f"Error uploading image: {e}")
        return None


# Route om een listing toe te voegen
@main.route('/add_listing', methods=['POST', 'GET'])
@login_required
def add_listing():
    if request.method == 'POST':
        # Haal data uit het formulier
        book_title = request.form.get('book_title')
        book_author = request.form.get('book_author')
        isbn = request.form.get('isbn')
        year = request.form.get('year')
        description = request.form.get('description')
        price = request.form.get('price')
        condition = request.form.get('condition')
        image_file = request.files.get('image_file')

        # Upload afbeelding naar Supabase
        public_url = None
        if image_file and allowed_file(image_file.filename):
            public_url = upload_image_to_supabase(image_file)
            if not public_url:
                flash("Er was een probleem bij het uploaden van de afbeelding.", "danger")
                return redirect(url_for('main.add_listing'))

        # Boek toevoegen of ophalen
        book = Book.query.filter_by(title=book_title, author=book_author).first()
        if not book:
            book = Book(title=book_title, author=book_author, isbn=isbn, year=year, description=description)
            db.session.add(book)
            db.session.commit()

        # Listing aanmaken
        new_listing = Listing(
            price=price,
            condition=condition,
            status="Available",
            user_id=current_user.user_id,
            book_id=book.book_id
        )
        db.session.add(new_listing)
        db.session.commit()

        # Afbeelding koppelen aan listing
        if public_url:
            new_image = ImageFile(file_path=public_url, listing_id=new_listing.listing_id)
            db.session.add(new_image)
            db.session.commit()

        flash("Listing succesvol toegevoegd!", "success")
        return redirect(url_for('main.my_listings'))

    return render_template('add_listing.html')


# Route om alle listings van de huidige gebruiker te bekijken
@main.route('/my_listings')
@login_required
def my_listings():
    listings = Listing.query.filter_by(user_id=current_user.user_id).all()
    return render_template('my_listings.html', listings=listings)


# Edit Listing
# Edit Listing
@main.route('/edit_listings/<int:listing_id>', methods=['POST', 'GET'])
@login_required
def edit_listings(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    # Controleer of de gebruiker de eigenaar is
    if listing.user_id != current_user.user_id:
        flash("You are not authorized to edit this listing.", "danger")
        return redirect(url_for('main.my_listings'))

    if request.method == 'POST':
        # Haal gegevens op uit het formulier
        listing.book.title = request.form.get('book_title')
        listing.book.author = request.form.get('book_author')
        listing.book.isbn = request.form.get('isbn')
        listing.book.year = request.form.get('year')
        listing.book.description = request.form.get('description')
        listing.price = request.form.get('price')
        listing.condition = request.form.get('condition')
        listing.status = request.form.get('status')

        # Controleer of er een nieuwe afbeelding is geüpload
        image_file = request.files.get('image_file')
        if image_file and allowed_file(image_file.filename):
            # Upload nieuwe afbeelding naar Supabase
            new_image_url = upload_image_to_supabase(image_file)

            if new_image_url:
                # Verwijder oude afbeelding uit Supabase (optioneel)
                if listing.image_files and len(listing.image_files) > 0:
                    old_image_path = listing.image_files[0].file_path.split("/")[-1]  # Haal alleen het bestandspad op
                    supabase.storage.from_("foto").remove([f"uploads/{old_image_path}"])

                # Sla de nieuwe afbeelding op in de database
                listing.image_files[0].file_path = new_image_url

        # Wijzigingen opslaan in de database
        db.session.commit()
        flash("Listing updated successfully!", "success")
        return redirect(url_for('main.my_listings'))

    return render_template('edit_listings.html', listing=listing)

# delete listings
@main.route('/delete_listing/<int:listing_id>', methods=['POST'])
@login_required
def delete_listing(listing_id):
    try:
        # Fetch the listing with the related book eagerly loaded
        listing = db.session.query(Listing).filter_by(listing_id=listing_id).options(db.joinedload(Listing.book)).first()

        if not listing:
            flash("Listing not found.", "danger")
            return redirect(url_for('main.my_listings'))

        # Ensure the current user owns the listing
        if listing.user_id != current_user.user_id:
            flash("You do not have permission to delete this listing.", "danger")
            return redirect(url_for('main.my_listings'))

        # Check if the listing is reserved or sold
        if listing.status in ['Reserved', 'Sold']:
            flash(f"The listing '{listing.book.title}' cannot be deleted because it is {listing.status.lower()}.", "warning")
            return redirect(url_for('main.my_listings'))

        # Delete associated favorites
        favorites = Favorite.query.filter_by(listing_id=listing_id).all()
        for favorite in favorites:
            db.session.delete(favorite)

        # Delete associated reviews
        reviews = Review.query.filter_by(listing_id=listing_id).all()
        for review in reviews:
            db.session.delete(review)

        # Delete the listing
        db.session.delete(listing)
        db.session.commit()

        flash(f"Listing '{listing.book.title}' successfully deleted!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the listing: {e}", "danger")

    return redirect(url_for('main.my_listings'))


# My favorites fucnties  
# Add to favorites 
@main.route('/add_to_favorites/<int:listing_id>', methods=['POST'])
@login_required
def add_to_favorites(listing_id):
    # Fetch the listing
    listing = Listing.query.get_or_404(listing_id)
    
    # Check if the listing is sold
    if listing.status == 'Sold':
        flash('You cannot add a sold listing to your favorites.', 'danger')
        return redirect(url_for('main.listing_detail', listing_id=listing_id))
    
    # Check if the listing belongs to the current user
    if listing.user_id == current_user.user_id:
        flash('You cannot add your own listing to your favorites.', 'danger')
        return redirect(url_for('main.listing_detail', listing_id=listing_id))
    
    # Check if the listing is already in favorites
    existing_favorite = Favorite.query.filter_by(user_id=current_user.user_id, listing_id=listing_id).first()
    if not existing_favorite:
        favorite = Favorite(user_id=current_user.user_id, listing_id=listing_id)
        db.session.add(favorite)
        db.session.commit()
        flash('Listing added to favorites!', 'success')
    else:
        flash('Listing is already in favorites!', 'warning')
    
    return redirect(url_for('main.my_favorites'))

#Remove from favorites 
@main.route('/remove_from_favorites/<int:listing_id>', methods=['POST'])
@login_required
def remove_from_favorites(listing_id):
    favorite = Favorite.query.filter_by(user_id=current_user.user_id, listing_id=listing_id).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash('Listing removed from favorites!', 'success')
    else:
        flash('Listing was not found in your favorites.', 'warning')
    return redirect(url_for('main.my_favorites'))

# Mijn Favorieten
@main.route('/my_favorites')
@login_required
def my_favorites():
    # Haal de favorieten van de gebruiker op
    favorites = db.session.query(Favorite).join(Listing).filter(Favorite.user_id == current_user.user_id).all()
    return render_template('my_favorites.html', favorites=favorites)




# Functies met listing details 
from datetime import date

# Add review
@main.route('/add_review/<int:listing_id>', methods=['POST', 'GET'])
@login_required
def add_review(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if request.method == 'POST':
        comment = request.form['comment']
        rating = int(request.form['rating'])
        today = date.today()  # Automatically set today's date

        # Check if a review already exists for this user and listing
        existing_review = Review.query.filter_by(user_id=current_user.user_id, listing_id=listing_id).first()
        if existing_review:
            flash("You have already posted a review for this listing.", "danger")
            return redirect(url_for('main.listing_detail', listing_id=listing_id))

        review = Review(comment=comment, rating=rating, date=today, user_id=current_user.user_id, listing_id=listing_id)
        db.session.add(review)
        db.session.commit()
        flash("Review successfully added!", "success")
        return redirect(url_for('main.listing_detail', listing_id=listing_id))
    return render_template('add_review.html', listing=listing)

# View Listing Details
@main.route('/listing_detail/<int:listing_id>', methods=['GET'])
def listing_detail(listing_id):
    listing = Listing.query.options(db.joinedload(Listing.image_files)).get_or_404(listing_id)
    reviews = Review.query.filter_by(listing_id=listing_id).all()  # Fetch reviews
    return render_template('listing_detail.html', listing=listing, reviews=reviews)

# Search Listings
@main.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if not query:
        flash("Voer een geldige zoekterm in.", "warning")
        return redirect(url_for('main.index'))
    
    results = Listing.query.join(Book).filter(
        (Book.title.ilike(f"%{query}%")) | (Book.author.ilike(f"%{query}%"))
    ).all()

    if not results:
        flash("Geen resultaten gevonden voor je zoekopdracht.", "info")

    return render_template('search_results.html', results=results, query=query)


# Transactions & reserverings functies 
# Transactions
@main.route('/buy_listing/<int:listing_id>', methods=['POST'])
@login_required
def buy_listing(listing_id):
    try:
        # Fetch the listing or return 404 if it doesn't exist
        listing = Listing.query.get_or_404(listing_id)

        # Prevent users from buying their own listings
        if listing.user_id == current_user.user_id:
            flash("You cannot purchase your own listing.", "danger")
            return redirect(url_for('main.listing_detail', listing_id=listing_id))

        # Ensure the listing is available for purchase
        if listing.status != 'Available':
            flash("This listing is not available for purchase.", "danger")
            return redirect(url_for('main.listing_detail', listing_id=listing_id))

        # Create a new transaction with the current timestamp
        new_transaction = Transaction(
            user_id=current_user.user_id,
            listing_id=listing_id,
            timestamp=datetime.now()
        )

        # Update the listing status to "Sold"
        listing.status = 'Sold'

        # Add transaction and commit changes
        db.session.add(new_transaction)
        db.session.commit()

        flash("You have successfully purchased this listing!", "success")
    except Exception as e:
        db.session.rollback()  # Roll back in case of error
        flash("An error occurred while processing your purchase.", "danger")
        print(f"Error: {e}")  # Log the error for debugging purposes

    # Redirect back to the user's listi6ngs or another page
    return redirect(url_for('main.index'))

# My purchases
@main.route('/my_purchases')
@login_required
def my_purchases():
    purchases = db.session.query(Transaction, Listing).join(Listing).filter(
        Transaction.user_id == current_user.user_id
    ).all()
    return render_template('my_purchases.html', purchases=purchases)

# Reserve a listing 
@main.route('/reserve_listing/<int:listing_id>', methods=['POST'])
@login_required
def reserve_listing(listing_id):
    try:
        # Fetch the listing or return 404 if it doesn't exist
        listing = Listing.query.get_or_404(listing_id)

        # Ensure the listing is available for reservation
        if listing.status != 'Available':
            flash("This listing is not available for reservation.", "danger")
            return redirect(url_for('main.listing_detail', listing_id=listing_id))

        # Ensure the current user is not the owner of the listing
        if listing.user_id == current_user.user_id:
            flash("You cannot reserve your own listing.", "danger")
            return redirect(url_for('main.listing_detail', listing_id=listing_id))

        # Create a new reservation
        new_reservation = Reservation(
            user_id=current_user.user_id,
            listing_id=listing_id,
            timestamp=datetime.now()
        )

        # Update the listing status to "Reserved"
        listing.status = 'Reserved'

        db.session.add(new_reservation)
        db.session.commit()

        flash("You have successfully reserved this listing!", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while processing your reservation.", "danger")
        print(f"Error: {e}")

    return redirect(url_for('main.my_reservations'))


#Delete reservation 
@main.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def delete_reservation(reservation_id):
    try:
        # Fetch the reservation or return 404 if it doesn't exist
        reservation = Reservation.query.get_or_404(reservation_id)

        # Ensure the current user owns the reservation
        if reservation.user_id != current_user.user_id:
            flash("You do not have permission to delete this reservation.", "danger")
            return redirect(url_for('main.my_reservations'))

        # Set the listing status back to 'Available'
        reservation.listing.status = 'Available'

        # Delete the reservation
        db.session.delete(reservation)
        db.session.commit()

        flash("Reservation successfully deleted!", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while trying to delete the reservation.", "danger")
        print(f"Error: {e}")

    return redirect(url_for('main.my_reservations'))

# Mijn Reserveringen
@main.route('/my_reservations')
@login_required
def my_reservations():
    reservations = db.session.query(Reservation, Listing).join(Listing).filter(
        Reservation.user_id == current_user.user_id
    ).all()
    return render_template('my_reservations.html', reservations=reservations)

# Buy Reserved Listing
@main.route('/buy_reserved_listing/<int:listing_id>/<int:reservation_id>', methods=['POST'])
@login_required
def buy_reserved_listing(listing_id, reservation_id):
    try:
        # Fetch the listing or return 404 if it doesn't exist
        listing = Listing.query.get_or_404(listing_id)

        # Fetch the reservation to verify ownership
        reservation = Reservation.query.get_or_404(reservation_id)

        # Ensure the reservation belongs to the current user
        if reservation.user_id != current_user.user_id:
            flash("You do not have permission to buy this reserved listing.", "danger")
            return redirect(url_for('main.my_reservations'))

        # Ensure the listing is still reserved and matches the reservation
        if listing.status != 'Reserved':
            flash("This listing is no longer reserved and cannot be purchased.", "danger")
            return redirect(url_for('main.my_reservations'))

        # Create a new transaction
        new_transaction = Transaction(
            user_id=current_user.user_id,
            listing_id=listing_id,
            timestamp=datetime.now()
        )

        # Update the listing status to "Sold"
        listing.status = 'Sold'

        # Remove the reservation
        db.session.delete(reservation)

        # Commit changes to the database
        db.session.add(new_transaction)
        db.session.commit()

        flash("You have successfully purchased this reserved listing!", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while processing your purchase.", "danger")
        print(f"Error: {e}")

    return redirect(url_for('main.my_purchases'))
