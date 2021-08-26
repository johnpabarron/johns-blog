from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

from sqlalchemy import Table, Column, Integer, ForeignKey

from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CreateNewUser, LoginUser, CommentForm
from flask_gravatar import Gravatar

#from sqlalchemy.ext.declarative import declarative_base

#Base = declarative_base()


from functools import wraps



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


#Initiate login manager
login_manager = LoginManager()
login_manager.init_app(app)

#Need this decorator and code to make other pages work
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)

#creates a decorator that only allows user with id '1' to access certain functions
def admin_only(f):
    #need to import 'wraps' from 'functools'
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.id != 1:
            #requires import of 'abort' from 'flask'
            return  abort(403)
        return f(*args, **kwargs)
    return wrapper



##CONFIGURE TABLES
class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), unique=True, nullable=False)
    posts = relationship("BlogPost", back_populates = "author")
    comment = relationship("Comment", back_populates = "comment_author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, ForeignKey("users.id"))
    author = relationship("Users", back_populates = "posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comment = relationship("Comment", back_populates = "parent_post")

    #owner = db.relationship("Users", back_populates="posts")

class Comment(db.Model):
    __tablename__="comments"
    id = db.Column(db.Integer, primary_key = True)
    author_id = db.Column(Integer, ForeignKey("users.id"))

    comment_author = relationship("Users", back_populates="comment")
    text = db.Column(db.Text, nullable = False)
    post_id = db.Column(db.Integer, ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates = "comment")



#db.create_all()




@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()

    return render_template("index.html", all_posts=posts)


@app.route('/register', methods= ['GET','POST'])
def register():

    form = CreateNewUser()
    if form.validate_on_submit():
        email_check = Users.query.filter_by(email=form.email.data).first()
        if email_check:
            flash("sorry, that email already exists")
            return redirect(url_for('register'))

        else:
            encrypted_password = generate_password_hash(password=form.password.data, method="pbkdf2:sha256", salt_length=8)

            new_user = Users(user_name= form.name.data,
                            email = form.email.data,
                            password = encrypted_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form = form)


@app.route('/login', methods = ["POST","GET"])
def login():
    form = LoginUser()
    if form.validate_on_submit():
        user = Users.query.filter_by(email= form.email.data).first()
        user_password = form.password.data
        if user:
            if check_password_hash(pwhash=user.password, password=user_password):

                login_user(user=user)
                # user_id = str(current_user.id).encode("utf-8")
                # load_user(user_id=user_id)
                # next = request.args.get('next')
                # if not is_safe_url(next):
                #     return abort(400)

                return redirect(url_for('get_all_posts'))
            else:
                flash("Sorry, that's the wrong password")
        else:
            flash("Sorry, that email doesn't exist in our database")


    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods = ["GET", "POST"])
@login_required
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        new_comment = Comment(
            text = comment_form.text.data

        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, current_user = current_user, comment_form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods = ["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


requested_post = BlogPost.query.get(1)





if __name__ == "__main__":
    #app.run(host='0.0.0.0', port=5000)
    app.run(debug=True)