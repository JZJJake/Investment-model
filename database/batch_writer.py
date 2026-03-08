import logging
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from database.database import SessionLocal, engine
from database.models import CompanyScore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchWriter:
    """
    Asynchronous queue component to buffer records and perform bulk inserts/upserts
    when a threshold is reached, preventing database locks.
    """
    def __init__(self, batch_size: int = 500):
        self.batch_size = batch_size
        self.buffer = []

    def add(self, record: dict):
        """Add a record to the memory buffer."""
        self.buffer.append(record)
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """Flush the buffer to the database using bulk upsert/insert."""
        if not self.buffer:
            return

        db: Session = SessionLocal()
        try:
            # We determine dialect based on the engine name
            dialect_name = engine.name

            if dialect_name == "sqlite":
                stmt = sqlite_insert(CompanyScore).values(self.buffer)
                # SQLite upsert logic based on unique constraint
                stmt = stmt.on_conflict_do_update(
                    index_elements=['company_code'],
                    set_={
                        'physical_capacity_score': stmt.excluded.physical_capacity_score,
                        'financial_support_score': stmt.excluded.financial_support_score,
                        'strategic_intent_score': stmt.excluded.strategic_intent_score,
                        'local_limitation_score': stmt.excluded.local_limitation_score,
                        'last_updated': stmt.excluded.last_updated
                    }
                )
            elif dialect_name == "postgresql":
                stmt = pg_insert(CompanyScore).values(self.buffer)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['company_code'],
                    set_={
                        'physical_capacity_score': stmt.excluded.physical_capacity_score,
                        'financial_support_score': stmt.excluded.financial_support_score,
                        'strategic_intent_score': stmt.excluded.strategic_intent_score,
                        'local_limitation_score': stmt.excluded.local_limitation_score,
                        'last_updated': stmt.excluded.last_updated
                    }
                )
            elif dialect_name == "mysql":
                stmt = mysql_insert(CompanyScore).values(self.buffer)
                stmt = stmt.on_duplicate_key_update(
                    physical_capacity_score=stmt.inserted.physical_capacity_score,
                    financial_support_score=stmt.inserted.financial_support_score,
                    strategic_intent_score=stmt.inserted.strategic_intent_score,
                    local_limitation_score=stmt.inserted.local_limitation_score,
                    last_updated=stmt.inserted.last_updated
                )
            else:
                # Fallback to standard bulk insert (no upsert support guaranteed)
                logger.warning(f"Upsert not natively implemented for dialect {dialect_name}. Falling back to standard bulk insert.")
                db.bulk_insert_mappings(CompanyScore, self.buffer)
                db.commit()
                self.buffer.clear()
                return

            db.execute(stmt)
            db.commit()
            logger.info(f"Successfully flushed {len(self.buffer)} records to DB using {dialect_name} dialect.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to flush batch to DB: {e}")
            raise
        finally:
            self.buffer.clear()
            db.close()
