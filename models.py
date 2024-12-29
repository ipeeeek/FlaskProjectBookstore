from sqlalchemy import Boolean, Column, DECIMAL, Date, DateTime, ForeignKey, Identity, Index, Integer, LargeBinary, String, Table, Unicode
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()
metadata = Base.metadata


class AdminUser(Base):
    __tablename__ = 'admin_user'

    admin_user_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    first_name = Column(Unicode(50), nullable=False)
    last_name = Column(Unicode(50), nullable=False)
    email = Column(Unicode(255), nullable=False, unique=True)
    password_hash = Column(LargeBinary(64), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_login = Column(DateTime)


class Author(Base):
    __tablename__ = 'author'

    author_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    first_name = Column(Unicode(50), nullable=False)
    last_name = Column(Unicode(50), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    bio = Column(Unicode)
    path_to_image = Column(Unicode(255))

    book_author = relationship('BookAuthor', back_populates='author')


class BookFormat(Base):
    __tablename__ = 'book_format'

    book_format_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    book_format_name = Column(Unicode(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='book_format')


class BookLanguage(Base):
    __tablename__ = 'book_language'

    book_language_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    book_language_name = Column(Unicode(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='book_language')


class Category(Base):
    __tablename__ = 'category'

    category_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    category_name = Column(Unicode(100), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book_category = relationship('BookCategory', back_populates='category')


class Country(Base):
    __tablename__ = 'country'

    country_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    country_name = Column(Unicode(100), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    province = relationship('Province', back_populates='country')
    shipping_address = relationship('ShippingAddress', back_populates='country')


class Customer(Base):
    __tablename__ = 'customer'

    customer_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    first_name = Column(Unicode(50), nullable=False)
    last_name = Column(Unicode(50), nullable=False)
    phone_number = Column(String(15, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    email = Column(Unicode(255), nullable=False, unique=True)
    password_hash = Column(LargeBinary(64), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    cart = relationship('Cart', back_populates='customer')
    favorite = relationship('Favorite', back_populates='customer')
    payment = relationship('Payment', back_populates='customer')
    in_stock_notification_subscription = relationship('InStockNotificationSubscription', back_populates='customer')
    rating = relationship('Rating', back_populates='customer')
    shipping_address = relationship('ShippingAddress', back_populates='customer')
    customer_order = relationship('CustomerOrder', back_populates='customer')


class Dimension(Base):
    __tablename__ = 'dimension'

    dimension_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    height = Column(DECIMAL(4, 2), nullable=False)
    width = Column(DECIMAL(4, 2), nullable=False)
    depth = Column(DECIMAL(4, 2), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='dimension')


class Genre(Base):
    __tablename__ = 'genre'

    genre_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    genre_name = Column(Unicode(50), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book_genre = relationship('BookGenre', back_populates='genre')


class OrderStatus(Base):
    __tablename__ = 'order_status'

    order_status_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    order_status_name = Column(Unicode(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    customer_order = relationship('CustomerOrder', back_populates='order_status')


class PaymentMethod(Base):
    __tablename__ = 'payment_method'

    payment_method_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    payment_method_name = Column(Unicode(50), nullable=False, unique=True)

    payment = relationship('Payment', back_populates='payment_method')


class PaymentStatus(Base):
    __tablename__ = 'payment_status'

    payment_status_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    payment_status_name = Column(Unicode(50), nullable=False, unique=True)

    payment = relationship('Payment', back_populates='payment_status')


class Publisher(Base):
    __tablename__ = 'publisher'

    publisher_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    publisher_name = Column(Unicode(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='publisher')


class Sysdiagrams(Base):
    __tablename__ = 'sysdiagrams'
    __table_args__ = (
        Index('UK_principal_name', 'principal_id', 'name', unique=True),
    )

    name = Column(Unicode(128), nullable=False)
    principal_id = Column(Integer, nullable=False)
    diagram_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    version = Column(Integer)
    definition = Column(LargeBinary)


t_vw_out_of_stock_books = Table(
    'vw_out_of_stock_books', metadata,
    Column('book_id', Integer, Identity(), nullable=False),
    Column('title', Unicode(255), nullable=False),
    Column('stock_quantity', Integer, nullable=False)
)


t_vw_sold_books = Table(
    'vw_sold_books', metadata,
    Column('book_id', Integer, nullable=False),
    Column('title', Unicode(255), nullable=False),
    Column('total_quantity_sold', Integer)
)


class Book(Base):
    __tablename__ = 'book'

    book_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    title = Column(Unicode(255), nullable=False, index=True)
    isbn = Column(Unicode(13), nullable=False, unique=True)
    publication_date = Column(Date, nullable=False)
    price = Column(DECIMAL(18, 2), nullable=False, index=True)
    stock_quantity = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=False)
    dimension_id = Column(ForeignKey('dimension.dimension_id'), nullable=False)
    book_format_id = Column(ForeignKey('book_format.book_format_id'), nullable=False)
    book_language_id = Column(ForeignKey('book_language.book_language_id'), nullable=False)
    publisher_id = Column(ForeignKey('publisher.publisher_id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    cover_image_path = Column(Unicode(255))
    synopsis = Column(Unicode)
    average_rating = Column(DECIMAL(1, 1))

    book_format = relationship('BookFormat', back_populates='book')
    book_language = relationship('BookLanguage', back_populates='book')
    dimension = relationship('Dimension', back_populates='book')
    publisher = relationship('Publisher', back_populates='book')
    book_author = relationship('BookAuthor', back_populates='book')
    book_category = relationship('BookCategory', back_populates='book')
    book_genre = relationship('BookGenre', back_populates='book')
    cart_book = relationship('CartBook', back_populates='book')
    favorite_book = relationship('FavoriteBook', back_populates='book')
    in_stock_notification_subscription = relationship('InStockNotificationSubscription', back_populates='book')
    rating = relationship('Rating', back_populates='book')
    customer_order_book = relationship('CustomerOrderBook', back_populates='book')


class Cart(Base):
    __tablename__ = 'cart'

    cart_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    customer_id = Column(ForeignKey('customer.customer_id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    customer = relationship('Customer', back_populates='cart')
    cart_book = relationship('CartBook', back_populates='cart')


class Favorite(Base):
    __tablename__ = 'favorite'

    favorite_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    customer_id = Column(ForeignKey('customer.customer_id'), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    customer = relationship('Customer', back_populates='favorite')
    favorite_book = relationship('FavoriteBook', back_populates='favorite')


class Payment(Base):
    __tablename__ = 'payment'

    payment_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    customer_id = Column(ForeignKey('customer.customer_id'), nullable=False, index=True)
    payment_method_id = Column(ForeignKey('payment_method.payment_method_id'), nullable=False)
    payment_status_id = Column(ForeignKey('payment_status.payment_status_id'), nullable=False)
    total_amount = Column(DECIMAL(18, 2), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    customer = relationship('Customer', back_populates='payment')
    payment_method = relationship('PaymentMethod', back_populates='payment')
    payment_status = relationship('PaymentStatus', back_populates='payment')
    customer_order = relationship('CustomerOrder', back_populates='payment')


class Province(Base):
    __tablename__ = 'province'

    province_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    country_id = Column(ForeignKey('country.country_id'), nullable=False, index=True)
    province_name = Column(Unicode(100), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    country = relationship('Country', back_populates='province')
    district = relationship('District', back_populates='province')
    shipping_address = relationship('ShippingAddress', back_populates='province')


class BookAuthor(Base):
    __tablename__ = 'book_author'

    book_id = Column(ForeignKey('book.book_id'), primary_key=True, nullable=False)
    author_id = Column(ForeignKey('author.author_id'), primary_key=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    author = relationship('Author', back_populates='book_author')
    book = relationship('Book', back_populates='book_author')


class BookCategory(Base):
    __tablename__ = 'book_category'

    book_id = Column(ForeignKey('book.book_id'), primary_key=True, nullable=False)
    category_id = Column(ForeignKey('category.category_id'), primary_key=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='book_category')
    category = relationship('Category', back_populates='book_category')


class BookGenre(Base):
    __tablename__ = 'book_genre'

    book_id = Column(ForeignKey('book.book_id'), primary_key=True, nullable=False)
    genre_id = Column(ForeignKey('genre.genre_id'), primary_key=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='book_genre')
    genre = relationship('Genre', back_populates='book_genre')


class CartBook(Base):
    __tablename__ = 'cart_book'

    cart_id = Column(ForeignKey('cart.cart_id'), primary_key=True, nullable=False)
    book_id = Column(ForeignKey('book.book_id'), primary_key=True, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='cart_book')
    cart = relationship('Cart', back_populates='cart_book')


class District(Base):
    __tablename__ = 'district'

    district_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    province_id = Column(ForeignKey('province.province_id'), nullable=False, index=True)
    district_name = Column(Unicode(100), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    province = relationship('Province', back_populates='district')
    neighborhood = relationship('Neighborhood', back_populates='district')
    postal_code = relationship('PostalCode', back_populates='district')
    shipping_address = relationship('ShippingAddress', back_populates='district')


class FavoriteBook(Base):
    __tablename__ = 'favorite_book'

    favorite_id = Column(ForeignKey('favorite.favorite_id'), primary_key=True, nullable=False)
    book_id = Column(ForeignKey('book.book_id'), primary_key=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='favorite_book')
    favorite = relationship('Favorite', back_populates='favorite_book')


class InStockNotificationSubscription(Base):
    __tablename__ = 'in_stock_notification_subscription'

    in_stock_notification_subscription_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    customer_id = Column(ForeignKey('customer.customer_id'), nullable=False)
    book_id = Column(ForeignKey('book.book_id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    notification_enabled = Column(Boolean)

    book = relationship('Book', back_populates='in_stock_notification_subscription')
    customer = relationship('Customer', back_populates='in_stock_notification_subscription')
    in_stock_notification_queue = relationship('InStockNotificationQueue', back_populates='in_stock_notification_subscription')


class Rating(Base):
    __tablename__ = 'rating'
    __table_args__ = (
        Index('unique_customer_book', 'customer_id', 'book_id', unique=True),
    )

    rating_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    customer_id = Column(ForeignKey('customer.customer_id'), nullable=False)
    book_id = Column(ForeignKey('book.book_id'), nullable=False, index=True)
    rating_value = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='rating')
    customer = relationship('Customer', back_populates='rating')


class InStockNotificationQueue(Base):
    __tablename__ = 'in_stock_notification_queue'

    in_stock_notification_queue_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    in_stock_notification_subscription_id = Column(ForeignKey('in_stock_notification_subscription.in_stock_notification_subscription_id'), nullable=False)
    notification_status = Column(Unicode(20), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    in_stock_notification_subscription = relationship('InStockNotificationSubscription', back_populates='in_stock_notification_queue')


class Neighborhood(Base):
    __tablename__ = 'neighborhood'

    neighborhood_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    district_id = Column(ForeignKey('district.district_id'), nullable=False, index=True)
    neighborhood_name = Column(Unicode(100), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    district = relationship('District', back_populates='neighborhood')
    street = relationship('Street', back_populates='neighborhood')
    shipping_address = relationship('ShippingAddress', back_populates='neighborhood')


class PostalCode(Base):
    __tablename__ = 'postal_code'

    postal_code_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    district_id = Column(ForeignKey('district.district_id'), nullable=False, index=True)
    postal_code = Column(Unicode(10), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    district = relationship('District', back_populates='postal_code')
    shipping_address = relationship('ShippingAddress', back_populates='postal_code')


class Street(Base):
    __tablename__ = 'street'

    street_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    neighborhood_id = Column(ForeignKey('neighborhood.neighborhood_id'), nullable=False, index=True)
    street_name = Column(Unicode(100), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    neighborhood = relationship('Neighborhood', back_populates='street')
    shipping_address = relationship('ShippingAddress', back_populates='street')


class ShippingAddress(Base):
    __tablename__ = 'shipping_address'

    shipping_address_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    customer_id = Column(ForeignKey('customer.customer_id'), nullable=False)
    country_id = Column(ForeignKey('country.country_id'), nullable=False)
    province_id = Column(ForeignKey('province.province_id'), nullable=False)
    district_id = Column(ForeignKey('district.district_id'), nullable=False)
    neighborhood_id = Column(ForeignKey('neighborhood.neighborhood_id'), nullable=False)
    street_id = Column(ForeignKey('street.street_id'), nullable=False)
    postal_code_id = Column(ForeignKey('postal_code.postal_code_id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    country = relationship('Country', back_populates='shipping_address')
    customer = relationship('Customer', back_populates='shipping_address')
    district = relationship('District', back_populates='shipping_address')
    neighborhood = relationship('Neighborhood', back_populates='shipping_address')
    postal_code = relationship('PostalCode', back_populates='shipping_address')
    province = relationship('Province', back_populates='shipping_address')
    street = relationship('Street', back_populates='shipping_address')
    customer_order = relationship('CustomerOrder', back_populates='shipping_address')


class CustomerOrder(Base):
    __tablename__ = 'customer_order'

    customer_order_id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    customer_id = Column(ForeignKey('customer.customer_id'), nullable=False, index=True)
    shipping_address_id = Column(ForeignKey('shipping_address.shipping_address_id'), nullable=False)
    order_status_id = Column(ForeignKey('order_status.order_status_id'), nullable=False)
    payment_id = Column(ForeignKey('payment.payment_id'), nullable=False)
    total_amount = Column(DECIMAL(18, 2), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    customer = relationship('Customer', back_populates='customer_order')
    order_status = relationship('OrderStatus', back_populates='customer_order')
    payment = relationship('Payment', back_populates='customer_order')
    shipping_address = relationship('ShippingAddress', back_populates='customer_order')
    customer_order_book = relationship('CustomerOrderBook', back_populates='customer_order')


class CustomerOrderBook(Base):
    __tablename__ = 'customer_order_book'

    customer_order_id = Column(ForeignKey('customer_order.customer_order_id'), primary_key=True, nullable=False)
    book_id = Column(ForeignKey('book.book_id'), primary_key=True, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    book = relationship('Book', back_populates='customer_order_book')
    customer_order = relationship('CustomerOrder', back_populates='customer_order_book')
