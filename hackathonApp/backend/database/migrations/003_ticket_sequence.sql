-- Migration 003: Create ticket number sequence
-- Fixes race condition in ticket numbering (TOCTOU vulnerability)
-- Uses PostgreSQL sequence for atomic, lock-free ticket number generation
-- Safe when run before or after the tickets table exists.

CREATE SEQUENCE IF NOT EXISTS ticket_number_seq START WITH 1 INCREMENT BY 1;

-- Seed the sequence to the current max ticket_number only if tickets table exists.
-- setval(seq, 0) is invalid (sequence minimum is 1). Use 1 when empty so next nextval() returns 1.
DO $$
DECLARE
  max_ticket BIGINT;
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'tickets') THEN
    SELECT COALESCE(MAX(ticket_number), 0) INTO max_ticket FROM tickets;
    IF max_ticket < 1 THEN
      PERFORM setval('ticket_number_seq', 1, false);  -- next nextval() will return 1
    ELSE
      PERFORM setval('ticket_number_seq', max_ticket);
    END IF;
  ELSE
    PERFORM setval('ticket_number_seq', 1, false);
  END IF;
END $$;
