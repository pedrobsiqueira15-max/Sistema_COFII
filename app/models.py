from datetime import date, datetime

from passlib.hash import bcrypt

from app.extensions import db, login_manager


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password: str) -> bool:
        return bcrypt.verify(password, self.password_hash)

    def get_id(self):  # Flask-Login
        return str(self.id)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


class Segment(db.Model):
    __tablename__ = "segments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AnalystWeight(db.Model):
    __tablename__ = "analyst_weights"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    segment_id = db.Column(db.Integer, db.ForeignKey("segments.id"), nullable=False)
    meeting_date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "segment_id", "meeting_date", name="uq_user_seg_date"),
    )


class BenchmarkWeight(db.Model):
    __tablename__ = "benchmark_weights"

    id = db.Column(db.Integer, primary_key=True)
    segment_id = db.Column(db.Integer, db.ForeignKey("segments.id"), nullable=False)
    as_of_date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class FundMetric(db.Model):
    __tablename__ = "fund_metrics"

    id = db.Column(db.Integer, primary_key=True)
    fund_code = db.Column(db.String(40), nullable=False)
    as_of_date = db.Column(db.Date, nullable=False)
    dy_12m = db.Column(db.Float, nullable=True)
    volatility = db.Column(db.Float, nullable=True)
    leverage = db.Column(db.Float, nullable=True)
    beta = db.Column(db.Float, nullable=True)
    p_vp = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("fund_code", "as_of_date", name="uq_fund_date"),
    )


class PortfolioFund(db.Model):
    __tablename__ = "portfolio_funds"

    id = db.Column(db.Integer, primary_key=True)
    fund_code = db.Column(db.String(40), nullable=False)
    segment_id = db.Column(db.Integer, db.ForeignKey("segments.id"), nullable=False)
    as_of_date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("fund_code", "as_of_date", name="uq_portfolio_fund_date"),
    )


class PortfolioMetricHistory(db.Model):
    __tablename__ = "portfolio_metric_history"

    id = db.Column(db.Integer, primary_key=True)
    as_of_date = db.Column(db.Date, nullable=False, unique=True)
    dy_12m = db.Column(db.Float, nullable=True)
    volatility = db.Column(db.Float, nullable=True)
    leverage = db.Column(db.Float, nullable=True)
    beta = db.Column(db.Float, nullable=True)
    p_vp = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
