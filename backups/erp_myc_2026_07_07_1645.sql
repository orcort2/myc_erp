--
-- PostgreSQL database dump
--

\restrict BcXx1Bw0pwFXmQVCGOl0FY7ehozlYIckdap1r6ym5LwYYsxd0xlwmoDo7Usr5DY

-- Dumped from database version 16.14 (Homebrew)
-- Dumped by pg_dump version 16.14 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: saulcortes
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO saulcortes;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: saulcortes
--

COMMENT ON SCHEMA public IS '';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO saulcortes;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.audit_logs (
    user_id integer,
    action character varying(120) NOT NULL,
    entity character varying(120) NOT NULL,
    entity_id integer,
    previous_values json,
    new_values json,
    comment character varying(500),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO saulcortes;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO saulcortes;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: calibration_procedures; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.calibration_procedures (
    code character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    magnitude character varying(80) NOT NULL,
    profile_key character varying(80),
    version character varying(40) NOT NULL,
    issuer_company character varying(40) NOT NULL,
    certificate_type character varying(40) NOT NULL,
    required_readings integer,
    decision_rule text,
    acceptance_criteria text,
    notes text,
    status character varying(40) NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    uncertainty_model_id integer,
    uncertainty_model_version_id integer
);


ALTER TABLE public.calibration_procedures OWNER TO saulcortes;

--
-- Name: calibration_procedures_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.calibration_procedures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.calibration_procedures_id_seq OWNER TO saulcortes;

--
-- Name: calibration_procedures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.calibration_procedures_id_seq OWNED BY public.calibration_procedures.id;


--
-- Name: catalog_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.catalog_items (
    item_type character varying(20) NOT NULL,
    commodity character varying(40) NOT NULL,
    category character varying(120) NOT NULL,
    internal_key character varying(80),
    name character varying(180) NOT NULL,
    description text,
    sat_key character varying(40),
    sat_unit character varying(40),
    internal_unit character varying(80),
    origin_price numeric(12,2) NOT NULL,
    origin_currency character varying(3) NOT NULL,
    exchange_rate numeric(12,6) NOT NULL,
    margin_percent numeric(8,4) NOT NULL,
    final_price_mxn numeric(12,2) NOT NULL,
    internal_cost numeric(12,2),
    cost_currency character varying(3),
    calibration_scope character varying(60),
    quotation_legend text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    custom_internal_unit character varying(80),
    tax_object character varying(20) DEFAULT 'iva_16'::character varying NOT NULL,
    tax_rate numeric(5,2) DEFAULT 16.00 NOT NULL
);


ALTER TABLE public.catalog_items OWNER TO saulcortes;

--
-- Name: catalog_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.catalog_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.catalog_items_id_seq OWNER TO saulcortes;

--
-- Name: catalog_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.catalog_items_id_seq OWNED BY public.catalog_items.id;


--
-- Name: certificates; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.certificates (
    folio character varying(40) NOT NULL,
    service_order_id integer NOT NULL,
    equipment_id integer NOT NULL,
    field_sheet_id integer,
    certificate_type character varying(40) NOT NULL,
    status character varying(60) NOT NULL,
    issued_on date,
    released_on date,
    title character varying(180),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    expected_folio character varying(40),
    final_pdf_path character varying(255),
    final_pdf_original_filename character varying(255),
    final_pdf_uploaded_at timestamp with time zone,
    final_pdf_uploaded_by_id integer,
    capture_started_at timestamp with time zone,
    capture_started_by_id integer,
    sent_to_quality_at timestamp with time zone,
    sent_to_quality_by_id integer,
    quality_reviewed_at timestamp with time zone,
    quality_reviewed_by_id integer,
    quality_rejection_reason text,
    released_to_client_at timestamp with time zone,
    released_to_client_by_id integer,
    external_source character varying(40) DEFAULT 'excel'::character varying NOT NULL,
    match_status character varying(40) DEFAULT 'pending'::character varying NOT NULL,
    match_details json,
    client_visible boolean DEFAULT false NOT NULL,
    authentication_code character varying(40),
    authentication_hash character varying(64),
    authenticated_pdf_path character varying(255),
    authenticated_pdf_generated_at timestamp with time zone,
    authenticated_by_id integer,
    verification_url character varying(255)
);


ALTER TABLE public.certificates OWNER TO saulcortes;

--
-- Name: certificates_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.certificates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.certificates_id_seq OWNER TO saulcortes;

--
-- Name: certificates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.certificates_id_seq OWNED BY public.certificates.id;


--
-- Name: client_contacts; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.client_contacts (
    client_id integer NOT NULL,
    name character varying(180) NOT NULL,
    email character varying(255),
    phone character varying(40),
    "position" character varying(120),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.client_contacts OWNER TO saulcortes;

--
-- Name: client_contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.client_contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.client_contacts_id_seq OWNER TO saulcortes;

--
-- Name: client_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.client_contacts_id_seq OWNED BY public.client_contacts.id;


--
-- Name: clients; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.clients (
    legal_name character varying(255) NOT NULL,
    commercial_name character varying(255),
    rfc character varying(13),
    email character varying(255),
    phone character varying(40),
    tax_regime character varying(120),
    payment_terms character varying(120),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    cfdi_use character varying(40),
    street character varying(255),
    exterior_number character varying(40),
    interior_number character varying(40),
    neighborhood character varying(180),
    city character varying(180),
    state character varying(180),
    postal_code character varying(20),
    country character varying(120),
    fiscal_postal_code character varying(20),
    tax_constancy_filename character varying(255),
    tax_constancy_path character varying(500),
    tax_constancy_uploaded_at timestamp with time zone,
    client_type character varying(30) DEFAULT 'persona_moral'::character varying NOT NULL,
    curp character varying(18),
    first_name character varying(120),
    first_last_name character varying(120),
    second_last_name character varying(120),
    street_type character varying(80),
    locality character varying(180),
    municipality character varying(180)
);


ALTER TABLE public.clients OWNER TO saulcortes;

--
-- Name: clients_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.clients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clients_id_seq OWNER TO saulcortes;

--
-- Name: clients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.clients_id_seq OWNED BY public.clients.id;


--
-- Name: controlled_document_versions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.controlled_document_versions (
    document_id integer NOT NULL,
    revision character varying(80) NOT NULL,
    file_path character varying(255),
    original_filename character varying(255),
    mime_type character varying(120),
    checksum character varying(128),
    change_summary text,
    uploaded_by_id integer,
    approved_by_id integer,
    reviewed_by_id integer,
    status character varying(40) NOT NULL,
    effective_date date,
    uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.controlled_document_versions OWNER TO saulcortes;

--
-- Name: controlled_document_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.controlled_document_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.controlled_document_versions_id_seq OWNER TO saulcortes;

--
-- Name: controlled_document_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.controlled_document_versions_id_seq OWNED BY public.controlled_document_versions.id;


--
-- Name: controlled_documents; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.controlled_documents (
    code character varying(80) NOT NULL,
    name character varying(255) NOT NULL,
    document_type character varying(60) NOT NULL,
    quality_level character varying(80),
    current_revision character varying(80),
    issue_date date,
    last_review_date date,
    effective_date date,
    retention_time character varying(120),
    digital_location character varying(255),
    status character varying(40) NOT NULL,
    description text,
    created_by_id integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.controlled_documents OWNER TO saulcortes;

--
-- Name: controlled_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.controlled_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.controlled_documents_id_seq OWNER TO saulcortes;

--
-- Name: controlled_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.controlled_documents_id_seq OWNED BY public.controlled_documents.id;


--
-- Name: credit_notes; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.credit_notes (
    invoice_id integer NOT NULL,
    folio character varying(40) NOT NULL,
    issued_on date,
    reason text NOT NULL,
    subtotal numeric(12,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    status character varying(40) NOT NULL,
    observations text,
    created_by_id integer,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.credit_notes OWNER TO saulcortes;

--
-- Name: credit_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.credit_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.credit_notes_id_seq OWNER TO saulcortes;

--
-- Name: credit_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.credit_notes_id_seq OWNED BY public.credit_notes.id;


--
-- Name: document_interpretations; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.document_interpretations (
    document_id integer NOT NULL,
    document_version_id integer,
    name character varying(255) NOT NULL,
    interpretation_type character varying(80) NOT NULL,
    magnitude character varying(80),
    equipment_type character varying(120),
    service_type character varying(80),
    calibration_scope character varying(40),
    data json,
    status character varying(40) NOT NULL,
    version integer NOT NULL,
    created_by_id integer,
    approved_by_id integer,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.document_interpretations OWNER TO saulcortes;

--
-- Name: document_interpretations_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.document_interpretations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_interpretations_id_seq OWNER TO saulcortes;

--
-- Name: document_interpretations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.document_interpretations_id_seq OWNED BY public.document_interpretations.id;


--
-- Name: document_templates; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.document_templates (
    template_key character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    company_name character varying(180) NOT NULL,
    company_tagline character varying(255),
    company_rfc character varying(20),
    company_email character varying(255),
    company_website character varying(255),
    company_address text,
    company_phone character varying(60),
    document_title character varying(120) NOT NULL,
    document_subtitle character varying(255),
    document_code character varying(80),
    document_revision character varying(80),
    document_issued_on date,
    terms_version character varying(80),
    commercial_terms text,
    metrological_terms text,
    legal_terms text,
    privacy_notice text,
    acceptance_text text,
    show_summary_terms boolean DEFAULT true NOT NULL,
    show_full_terms boolean DEFAULT true NOT NULL,
    show_acceptance_signature boolean DEFAULT true NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.document_templates OWNER TO saulcortes;

--
-- Name: document_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.document_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_templates_id_seq OWNER TO saulcortes;

--
-- Name: document_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.document_templates_id_seq OWNED BY public.document_templates.id;


--
-- Name: equipment; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.equipment (
    service_order_id integer NOT NULL,
    service_order_item_id integer,
    status character varying(60) NOT NULL,
    name character varying(180) NOT NULL,
    brand character varying(120),
    model character varying(120),
    serial_number character varying(120),
    internal_id character varying(120),
    range_or_capacity character varying(180),
    initial_condition text,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    calibration_scope character varying(60)
);


ALTER TABLE public.equipment OWNER TO saulcortes;

--
-- Name: equipment_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.equipment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipment_id_seq OWNER TO saulcortes;

--
-- Name: equipment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.equipment_id_seq OWNED BY public.equipment.id;


--
-- Name: field_sheet_reference_standards; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheet_reference_standards (
    field_sheet_id integer NOT NULL,
    reference_standard_id integer NOT NULL,
    usage_role character varying(40) NOT NULL,
    measurement_section character varying(80),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    reference_standard_certificate_id integer,
    selected_uncertainty_id integer,
    selection_status character varying(40),
    selection_notes text,
    validation_snapshot json
);


ALTER TABLE public.field_sheet_reference_standards OWNER TO saulcortes;

--
-- Name: field_sheet_reference_standards_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheet_reference_standards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheet_reference_standards_id_seq OWNER TO saulcortes;

--
-- Name: field_sheet_reference_standards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheet_reference_standards_id_seq OWNED BY public.field_sheet_reference_standards.id;


--
-- Name: field_sheet_results; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheet_results (
    field_sheet_id integer NOT NULL,
    section_key character varying(80) NOT NULL,
    row_number integer NOT NULL,
    pattern_value character varying(180),
    ibc_value_1 character varying(180),
    ibc_value_2 character varying(180),
    ibc_value_3 character varying(180),
    unit character varying(80),
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_data json
);


ALTER TABLE public.field_sheet_results OWNER TO saulcortes;

--
-- Name: field_sheet_results_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheet_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheet_results_id_seq OWNER TO saulcortes;

--
-- Name: field_sheet_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheet_results_id_seq OWNED BY public.field_sheet_results.id;


--
-- Name: field_sheet_template_definitions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheet_template_definitions (
    template_key character varying(60) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    status character varying(40) NOT NULL,
    version integer NOT NULL,
    definition_json json NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.field_sheet_template_definitions OWNER TO saulcortes;

--
-- Name: field_sheet_template_definitions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheet_template_definitions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheet_template_definitions_id_seq OWNER TO saulcortes;

--
-- Name: field_sheet_template_definitions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheet_template_definitions_id_seq OWNED BY public.field_sheet_template_definitions.id;


--
-- Name: field_sheets; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.field_sheets (
    equipment_id integer NOT NULL,
    status character varying(60) NOT NULL,
    initial_condition text,
    final_condition text,
    pattern_used character varying(180),
    results text,
    observations text,
    evidence_notes text,
    method character varying(180),
    environmental_conditions text,
    technician_notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    template_key character varying(40) NOT NULL,
    work_order_number integer,
    calibration_place character varying(180),
    reception_date date,
    calibration_date date,
    next_calibration_date date,
    environment_humidity_start character varying(40),
    environment_humidity_end character varying(40),
    environment_temperature_start character varying(40),
    environment_temperature_end character varying(40),
    equipment_general_condition boolean,
    consider_equipment_deviations boolean NOT NULL,
    units character varying(80),
    calibrated_by character varying(180),
    reviewed_by character varying(180),
    report_made_by character varying(180),
    purchase_order_or_quotation character varying(180),
    calibration_procedure_id integer,
    returned_to_technician_at timestamp with time zone,
    returned_to_technician_by_id integer,
    returned_to_technician_reason text,
    certificate_client_mode character varying(30) NOT NULL,
    certificate_client_company character varying(180),
    certificate_client_attention character varying(180),
    certificate_client_address text,
    apply_certificate_client_to_order boolean NOT NULL,
    minimum_division character varying(120),
    location character varying(180),
    attention character varying(180),
    company character varying(180),
    address text,
    template_definition_json json,
    template_definition_version integer
);


ALTER TABLE public.field_sheets OWNER TO saulcortes;

--
-- Name: field_sheets_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.field_sheets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.field_sheets_id_seq OWNER TO saulcortes;

--
-- Name: field_sheets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.field_sheets_id_seq OWNED BY public.field_sheets.id;


--
-- Name: invoice_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoice_items (
    invoice_id integer NOT NULL,
    quotation_item_id integer,
    certificate_id integer,
    equipment_id integer,
    description text NOT NULL,
    quantity numeric(12,2) NOT NULL,
    unit character varying(80),
    sat_unit character varying(40),
    sat_key character varying(40),
    unit_price numeric(12,2) NOT NULL,
    discount_total numeric(12,2) NOT NULL,
    tax_rate numeric(5,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    line_total numeric(12,2) NOT NULL,
    notes text,
    service_type character varying(80),
    source_type character varying(40),
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoice_items OWNER TO saulcortes;

--
-- Name: invoice_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoice_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_items_id_seq OWNER TO saulcortes;

--
-- Name: invoice_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoice_items_id_seq OWNED BY public.invoice_items.id;


--
-- Name: invoice_payments; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoice_payments (
    invoice_id integer NOT NULL,
    paid_on date,
    amount numeric(12,2) NOT NULL,
    bank_name character varying(120),
    bank_account character varying(120),
    reference character varying(120),
    payment_method character varying(80),
    payment_form character varying(80),
    status character varying(40) NOT NULL,
    notes text,
    registered_by_id integer,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoice_payments OWNER TO saulcortes;

--
-- Name: invoice_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoice_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_payments_id_seq OWNER TO saulcortes;

--
-- Name: invoice_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoice_payments_id_seq OWNED BY public.invoice_payments.id;


--
-- Name: invoice_settings; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoice_settings (
    key character varying(60) NOT NULL,
    default_series character varying(20) NOT NULL,
    next_sequence integer NOT NULL,
    reset_annually boolean NOT NULL,
    default_tax_rate numeric(5,2) NOT NULL,
    default_currency character varying(10) NOT NULL,
    default_credit_days integer NOT NULL,
    allow_manual_folio boolean NOT NULL,
    forms_of_payment json,
    methods_of_payment json,
    usage_cfdi_catalog json,
    tax_regime_catalog json,
    currency_catalog json,
    sat_product_keys json,
    sat_units json,
    banks json,
    bank_accounts json,
    legal_texts json,
    billing_emails json,
    emitter_data json,
    pdf_template_name character varying(120),
    cfdi_future_parameters json,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoice_settings OWNER TO saulcortes;

--
-- Name: invoice_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoice_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoice_settings_id_seq OWNER TO saulcortes;

--
-- Name: invoice_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoice_settings_id_seq OWNED BY public.invoice_settings.id;


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.invoices (
    internal_uuid character varying(64) NOT NULL,
    series character varying(20) NOT NULL,
    folio character varying(40) NOT NULL,
    client_id integer NOT NULL,
    fiscal_client_id integer,
    service_order_id integer,
    quotation_id integer,
    issued_on date,
    due_on date,
    subtotal numeric(12,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    withholding_total numeric(12,2) NOT NULL,
    discount_total numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    balance_due numeric(12,2) NOT NULL,
    amount_paid numeric(12,2) NOT NULL,
    status character varying(40) NOT NULL,
    payment_method character varying(80),
    payment_form character varying(80),
    usage_cfdi character varying(80),
    currency character varying(10) NOT NULL,
    credit_days integer NOT NULL,
    observations text,
    internal_comments text,
    cancellation_reason text,
    created_by_id integer,
    updated_by_id integer,
    last_payment_on date,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoices OWNER TO saulcortes;

--
-- Name: invoices_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoices_id_seq OWNER TO saulcortes;

--
-- Name: invoices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.invoices_id_seq OWNED BY public.invoices.id;


--
-- Name: quotation_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.quotation_items (
    quotation_id integer NOT NULL,
    service_name character varying(180) NOT NULL,
    description text,
    quantity integer NOT NULL,
    unit_price numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    catalog_item_id integer,
    unit character varying(80),
    currency character varying(3),
    commodity character varying(40),
    calibration_scope character varying(60),
    quotation_legend text,
    sat_key character varying(40),
    sat_unit character varying(40),
    internal_unit character varying(80),
    discount_percent numeric(8,4) DEFAULT 0.0000 NOT NULL,
    tax_object character varying(20),
    tax_rate numeric(5,2) DEFAULT 16.00 NOT NULL,
    tax_total numeric(12,2) DEFAULT 0.00 NOT NULL
);


ALTER TABLE public.quotation_items OWNER TO saulcortes;

--
-- Name: quotation_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.quotation_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotation_items_id_seq OWNER TO saulcortes;

--
-- Name: quotation_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.quotation_items_id_seq OWNED BY public.quotation_items.id;


--
-- Name: quotations; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.quotations (
    folio character varying(40) NOT NULL,
    client_id integer NOT NULL,
    status character varying(40) NOT NULL,
    issued_on date,
    valid_until date,
    subtotal numeric(12,2) NOT NULL,
    tax_total numeric(12,2) NOT NULL,
    total numeric(12,2) NOT NULL,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    advisor_id integer
);


ALTER TABLE public.quotations OWNER TO saulcortes;

--
-- Name: quotations_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.quotations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotations_id_seq OWNER TO saulcortes;

--
-- Name: quotations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.quotations_id_seq OWNED BY public.quotations.id;


--
-- Name: reference_standard_certificate_uncertainties; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standard_certificate_uncertainties (
    certificate_id integer NOT NULL,
    magnitude character varying(80),
    measurement_type character varying(120),
    range_min numeric(18,6),
    range_max numeric(18,6),
    unit character varying(40),
    uncertainty_value numeric(18,6) NOT NULL,
    uncertainty_unit character varying(40),
    k_factor numeric(12,6),
    confidence_level character varying(80),
    distribution character varying(80),
    formula_reference character varying(180),
    notes text,
    is_active boolean NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standard_certificate_uncertainties OWNER TO saulcortes;

--
-- Name: reference_standard_certificate_uncertainties_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standard_certificate_uncertainties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standard_certificate_uncertainties_id_seq OWNER TO saulcortes;

--
-- Name: reference_standard_certificate_uncertainties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standard_certificate_uncertainties_id_seq OWNED BY public.reference_standard_certificate_uncertainties.id;


--
-- Name: reference_standard_certificates; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standard_certificates (
    reference_standard_id integer NOT NULL,
    controlled_document_id integer,
    controlled_document_version_id integer,
    certificate_number character varying(120) NOT NULL,
    issuing_laboratory character varying(180),
    accreditation_body character varying(180),
    accreditation_number character varying(120),
    calibration_date date,
    expiration_date date,
    received_date date,
    status character varying(40) NOT NULL,
    is_current boolean NOT NULL,
    traceability_statement text,
    environmental_conditions text,
    notes text,
    created_by_id integer,
    approved_by_id integer,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standard_certificates OWNER TO saulcortes;

--
-- Name: reference_standard_certificates_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standard_certificates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standard_certificates_id_seq OWNER TO saulcortes;

--
-- Name: reference_standard_certificates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standard_certificates_id_seq OWNED BY public.reference_standard_certificates.id;


--
-- Name: reference_standard_uncertainties; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standard_uncertainties (
    reference_standard_id integer NOT NULL,
    range_min numeric(18,6),
    range_max numeric(18,6),
    unit character varying(40),
    uncertainty_value numeric(18,6) NOT NULL,
    coverage_factor_k numeric(12,6),
    distribution character varying(80),
    notes text,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standard_uncertainties OWNER TO saulcortes;

--
-- Name: reference_standard_uncertainties_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standard_uncertainties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standard_uncertainties_id_seq OWNER TO saulcortes;

--
-- Name: reference_standard_uncertainties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standard_uncertainties_id_seq OWNED BY public.reference_standard_uncertainties.id;


--
-- Name: reference_standards; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.reference_standards (
    internal_code character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    owner_company character varying(40) NOT NULL,
    magnitude character varying(80) NOT NULL,
    brand character varying(120),
    model character varying(120),
    serial_number character varying(120),
    identification character varying(120),
    unit character varying(40),
    range_min numeric(18,6),
    range_max numeric(18,6),
    resolution numeric(18,6),
    coverage_factor_k numeric(12,6),
    provider character varying(180),
    calibration_laboratory character varying(180),
    certificate_number character varying(120),
    certificate_file_path character varying(255),
    calibrated_on date,
    next_calibration_on date,
    status character varying(40) NOT NULL,
    notes text,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_standards OWNER TO saulcortes;

--
-- Name: reference_standards_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.reference_standards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_standards_id_seq OWNER TO saulcortes;

--
-- Name: reference_standards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.reference_standards_id_seq OWNED BY public.reference_standards.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.roles (
    name character varying(80) NOT NULL,
    description character varying(255),
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.roles OWNER TO saulcortes;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO saulcortes;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: service_order_items; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.service_order_items (
    service_order_id integer NOT NULL,
    quotation_item_id integer,
    service_name character varying(180) NOT NULL,
    quantity integer NOT NULL,
    status character varying(60) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    calibration_scope character varying(60)
);


ALTER TABLE public.service_order_items OWNER TO saulcortes;

--
-- Name: service_order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.service_order_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.service_order_items_id_seq OWNER TO saulcortes;

--
-- Name: service_order_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.service_order_items_id_seq OWNED BY public.service_order_items.id;


--
-- Name: service_orders; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.service_orders (
    folio character varying(40) NOT NULL,
    client_id integer NOT NULL,
    quotation_id integer,
    status character varying(60) NOT NULL,
    agenda_date date,
    closed_at date,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    advisor_id integer,
    technician_id integer,
    service_date date,
    total_equipment integer NOT NULL,
    completed_equipment integer NOT NULL,
    requires_payment boolean NOT NULL,
    work_order_number integer NOT NULL
);


ALTER TABLE public.service_orders OWNER TO saulcortes;

--
-- Name: service_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.service_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.service_orders_id_seq OWNER TO saulcortes;

--
-- Name: service_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.service_orders_id_seq OWNED BY public.service_orders.id;


--
-- Name: technical_profile_allowed_patterns; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.technical_profile_allowed_patterns (
    technical_profile_id integer NOT NULL,
    pattern_id integer,
    pattern_code character varying(120),
    min_range numeric(18,6),
    max_range numeric(18,6),
    unit character varying(40),
    priority integer,
    is_preferred boolean NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.technical_profile_allowed_patterns OWNER TO saulcortes;

--
-- Name: technical_profile_allowed_patterns_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.technical_profile_allowed_patterns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.technical_profile_allowed_patterns_id_seq OWNER TO saulcortes;

--
-- Name: technical_profile_allowed_patterns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.technical_profile_allowed_patterns_id_seq OWNED BY public.technical_profile_allowed_patterns.id;


--
-- Name: technical_profiles; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.technical_profiles (
    code character varying(120) NOT NULL,
    name character varying(255) NOT NULL,
    magnitude character varying(80) NOT NULL,
    equipment_type character varying(120) NOT NULL,
    service_type character varying(80) NOT NULL,
    calibration_scope character varying(40) NOT NULL,
    procedure_document_id integer,
    procedure_interpretation_id integer,
    field_sheet_template_document_id integer,
    certificate_template_document_id integer,
    uncertainty_source_document_id integer,
    status character varying(40) NOT NULL,
    version integer NOT NULL,
    rules json,
    notes text,
    created_by_id integer,
    approved_by_id integer,
    approved_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.technical_profiles OWNER TO saulcortes;

--
-- Name: technical_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.technical_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.technical_profiles_id_seq OWNER TO saulcortes;

--
-- Name: technical_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.technical_profiles_id_seq OWNED BY public.technical_profiles.id;


--
-- Name: uncertainty_calculations; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_calculations (
    field_sheet_id integer NOT NULL,
    uncertainty_model_id integer NOT NULL,
    status character varying(40) NOT NULL,
    calculated_at timestamp with time zone NOT NULL,
    calculation_snapshot json NOT NULL,
    input_snapshot json NOT NULL,
    component_results json NOT NULL,
    formula_results json NOT NULL,
    warnings json NOT NULL,
    errors json NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    uncertainty_model_version_id integer
);


ALTER TABLE public.uncertainty_calculations OWNER TO saulcortes;

--
-- Name: uncertainty_calculations_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_calculations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_calculations_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_calculations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_calculations_id_seq OWNED BY public.uncertainty_calculations.id;


--
-- Name: uncertainty_components; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_components (
    model_id integer NOT NULL,
    key character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    source_type character varying(60) NOT NULL,
    distribution character varying(60),
    divisor double precision,
    sensitivity_coefficient double precision NOT NULL,
    value_expression text,
    required boolean NOT NULL,
    sort_order integer NOT NULL,
    metadata_json json,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    model_version_id integer
);


ALTER TABLE public.uncertainty_components OWNER TO saulcortes;

--
-- Name: uncertainty_components_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_components_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_components_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_components_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_components_id_seq OWNED BY public.uncertainty_components.id;


--
-- Name: uncertainty_formulas; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_formulas (
    model_id integer NOT NULL,
    key character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    expression text NOT NULL,
    result_key character varying(80) NOT NULL,
    description text,
    sort_order integer NOT NULL,
    is_active_formula boolean NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    model_version_id integer
);


ALTER TABLE public.uncertainty_formulas OWNER TO saulcortes;

--
-- Name: uncertainty_formulas_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_formulas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_formulas_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_formulas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_formulas_id_seq OWNED BY public.uncertainty_formulas.id;


--
-- Name: uncertainty_model_exceptions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_model_exceptions (
    base_model_id integer,
    alternate_model_id integer NOT NULL,
    magnitude character varying(80),
    equipment_type character varying(180),
    equipment_model character varying(120),
    procedure_id integer,
    profile_key character varying(80),
    reason text NOT NULL,
    authorized_by_id integer,
    authorized_at timestamp with time zone,
    status character varying(40) NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer,
    base_model_version_id integer,
    alternate_model_version_id integer
);


ALTER TABLE public.uncertainty_model_exceptions OWNER TO saulcortes;

--
-- Name: uncertainty_model_exceptions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_model_exceptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_model_exceptions_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_model_exceptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_model_exceptions_id_seq OWNED BY public.uncertainty_model_exceptions.id;


--
-- Name: uncertainty_model_versions; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_model_versions (
    model_id integer NOT NULL,
    version_number character varying(40) NOT NULL,
    status character varying(40) DEFAULT 'draft'::character varying NOT NULL,
    change_summary text,
    default_coverage_factor double precision DEFAULT '2'::double precision NOT NULL,
    submitted_at timestamp with time zone,
    submitted_by_id integer,
    approved_at timestamp with time zone,
    approved_by_id integer,
    obsolete_at timestamp with time zone,
    archived_at timestamp with time zone,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.uncertainty_model_versions OWNER TO saulcortes;

--
-- Name: uncertainty_model_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_model_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_model_versions_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_model_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_model_versions_id_seq OWNED BY public.uncertainty_model_versions.id;


--
-- Name: uncertainty_models; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.uncertainty_models (
    code character varying(80) NOT NULL,
    name character varying(180) NOT NULL,
    description text,
    magnitude character varying(80) NOT NULL,
    equipment_family character varying(120),
    version character varying(40) NOT NULL,
    status character varying(40) NOT NULL,
    default_coverage_factor double precision NOT NULL,
    notes text,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.uncertainty_models OWNER TO saulcortes;

--
-- Name: uncertainty_models_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.uncertainty_models_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.uncertainty_models_id_seq OWNER TO saulcortes;

--
-- Name: uncertainty_models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.uncertainty_models_id_seq OWNED BY public.uncertainty_models.id;


--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.user_roles (
    user_id integer NOT NULL,
    role_id integer NOT NULL
);


ALTER TABLE public.user_roles OWNER TO saulcortes;

--
-- Name: users; Type: TABLE; Schema: public; Owner: saulcortes
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    full_name character varying(180) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    role_id integer,
    id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by integer
);


ALTER TABLE public.users OWNER TO saulcortes;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: saulcortes
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO saulcortes;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: saulcortes
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: calibration_procedures id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures ALTER COLUMN id SET DEFAULT nextval('public.calibration_procedures_id_seq'::regclass);


--
-- Name: catalog_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.catalog_items ALTER COLUMN id SET DEFAULT nextval('public.catalog_items_id_seq'::regclass);


--
-- Name: certificates id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates ALTER COLUMN id SET DEFAULT nextval('public.certificates_id_seq'::regclass);


--
-- Name: client_contacts id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.client_contacts ALTER COLUMN id SET DEFAULT nextval('public.client_contacts_id_seq'::regclass);


--
-- Name: clients id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.clients ALTER COLUMN id SET DEFAULT nextval('public.clients_id_seq'::regclass);


--
-- Name: controlled_document_versions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions ALTER COLUMN id SET DEFAULT nextval('public.controlled_document_versions_id_seq'::regclass);


--
-- Name: controlled_documents id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents ALTER COLUMN id SET DEFAULT nextval('public.controlled_documents_id_seq'::regclass);


--
-- Name: credit_notes id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes ALTER COLUMN id SET DEFAULT nextval('public.credit_notes_id_seq'::regclass);


--
-- Name: document_interpretations id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations ALTER COLUMN id SET DEFAULT nextval('public.document_interpretations_id_seq'::regclass);


--
-- Name: document_templates id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_templates ALTER COLUMN id SET DEFAULT nextval('public.document_templates_id_seq'::regclass);


--
-- Name: equipment id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment ALTER COLUMN id SET DEFAULT nextval('public.equipment_id_seq'::regclass);


--
-- Name: field_sheet_reference_standards id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards ALTER COLUMN id SET DEFAULT nextval('public.field_sheet_reference_standards_id_seq'::regclass);


--
-- Name: field_sheet_results id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results ALTER COLUMN id SET DEFAULT nextval('public.field_sheet_results_id_seq'::regclass);


--
-- Name: field_sheet_template_definitions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_template_definitions ALTER COLUMN id SET DEFAULT nextval('public.field_sheet_template_definitions_id_seq'::regclass);


--
-- Name: field_sheets id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets ALTER COLUMN id SET DEFAULT nextval('public.field_sheets_id_seq'::regclass);


--
-- Name: invoice_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items ALTER COLUMN id SET DEFAULT nextval('public.invoice_items_id_seq'::regclass);


--
-- Name: invoice_payments id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments ALTER COLUMN id SET DEFAULT nextval('public.invoice_payments_id_seq'::regclass);


--
-- Name: invoice_settings id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_settings ALTER COLUMN id SET DEFAULT nextval('public.invoice_settings_id_seq'::regclass);


--
-- Name: invoices id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices ALTER COLUMN id SET DEFAULT nextval('public.invoices_id_seq'::regclass);


--
-- Name: quotation_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items ALTER COLUMN id SET DEFAULT nextval('public.quotation_items_id_seq'::regclass);


--
-- Name: quotations id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations ALTER COLUMN id SET DEFAULT nextval('public.quotations_id_seq'::regclass);


--
-- Name: reference_standard_certificate_uncertainties id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificate_uncertainties ALTER COLUMN id SET DEFAULT nextval('public.reference_standard_certificate_uncertainties_id_seq'::regclass);


--
-- Name: reference_standard_certificates id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates ALTER COLUMN id SET DEFAULT nextval('public.reference_standard_certificates_id_seq'::regclass);


--
-- Name: reference_standard_uncertainties id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_uncertainties ALTER COLUMN id SET DEFAULT nextval('public.reference_standard_uncertainties_id_seq'::regclass);


--
-- Name: reference_standards id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standards ALTER COLUMN id SET DEFAULT nextval('public.reference_standards_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: service_order_items id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items ALTER COLUMN id SET DEFAULT nextval('public.service_order_items_id_seq'::regclass);


--
-- Name: service_orders id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders ALTER COLUMN id SET DEFAULT nextval('public.service_orders_id_seq'::regclass);


--
-- Name: technical_profile_allowed_patterns id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns ALTER COLUMN id SET DEFAULT nextval('public.technical_profile_allowed_patterns_id_seq'::regclass);


--
-- Name: technical_profiles id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles ALTER COLUMN id SET DEFAULT nextval('public.technical_profiles_id_seq'::regclass);


--
-- Name: uncertainty_calculations id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_calculations_id_seq'::regclass);


--
-- Name: uncertainty_components id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_components_id_seq'::regclass);


--
-- Name: uncertainty_formulas id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_formulas_id_seq'::regclass);


--
-- Name: uncertainty_model_exceptions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_model_exceptions_id_seq'::regclass);


--
-- Name: uncertainty_model_versions id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_model_versions_id_seq'::regclass);


--
-- Name: uncertainty_models id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_models ALTER COLUMN id SET DEFAULT nextval('public.uncertainty_models_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.alembic_version (version_num) FROM stdin;
2b3c4d5e6f7a
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.audit_logs (user_id, action, entity, entity_id, previous_values, new_values, comment, id, created_at, updated_at) FROM stdin;
\N	user.created	users	1	null	{"email": "saul@myc.com", "full_name": "admin", "is_active": true, "role_names": ["Administrador"]}	Registro inicial o alta desde auth.register	1	2026-07-07 13:27:43.740202-06	2026-07-07 13:27:43.740202-06
\N	client.created	clients	1	null	{"legal_name": "A quien corresponda", "rfc": null, "commercial_name": "A quien corresponda"}	\N	2	2026-07-07 13:28:01.44382-06	2026-07-07 13:28:01.44382-06
\N	client.created	clients	2	null	{"legal_name": "ABASTECEDORA DE INSUMOS PARA LA SALUD", "rfc": null, "commercial_name": "ABASTECEDORA DE INSUMOS PARA LA SALUD"}	\N	3	2026-07-07 13:28:01.519585-06	2026-07-07 13:28:01.519585-06
\N	client.created	clients	3	null	{"legal_name": "ADM Packaging Services S de RL de CV", "rfc": null, "commercial_name": "ADM Packaging Services S de RL de CV"}	\N	4	2026-07-07 13:28:01.526197-06	2026-07-07 13:28:01.526197-06
\N	client.created	clients	4	null	{"legal_name": "AGRO FRESAM", "rfc": null, "commercial_name": "AGRO FRESAM"}	\N	5	2026-07-07 13:28:01.532171-06	2026-07-07 13:28:01.532171-06
\N	client.created	clients	5	null	{"legal_name": "AGUA BLUE ROCK", "rfc": null, "commercial_name": "AGUA BLUE ROCK"}	\N	6	2026-07-07 13:28:01.538702-06	2026-07-07 13:28:01.538702-06
\N	client.created	clients	6	null	{"legal_name": "ALLIANCER S.A. DE C.V.", "rfc": null, "commercial_name": "ALLIANCER S.A. DE C.V."}	\N	7	2026-07-07 13:28:01.545399-06	2026-07-07 13:28:01.545399-06
\N	client.created	clients	7	null	{"legal_name": "AMMED", "rfc": null, "commercial_name": "AMMED"}	\N	8	2026-07-07 13:28:01.549201-06	2026-07-07 13:28:01.549201-06
\N	client.created	clients	8	null	{"legal_name": "APC Procesadora An\\u00e1huac, S.A. de C.V.", "rfc": null, "commercial_name": "APC Procesadora An\\u00e1huac, S.A. de C.V."}	\N	9	2026-07-07 13:28:01.553108-06	2026-07-07 13:28:01.553108-06
\N	client.created	clients	9	null	{"legal_name": "APX MS", "rfc": null, "commercial_name": "APX MS"}	\N	10	2026-07-07 13:28:01.557145-06	2026-07-07 13:28:01.557145-06
\N	client.created	clients	10	null	{"legal_name": "AVFRA INDUSTRIES", "rfc": null, "commercial_name": "AVFRA INDUSTRIES"}	\N	11	2026-07-07 13:28:01.560347-06	2026-07-07 13:28:01.560347-06
\N	client.created	clients	11	null	{"legal_name": "ARTURO DANIEL AMEZCUA MORA", "rfc": null, "commercial_name": "ARTURO DANIEL AMEZCUA MORA"}	\N	12	2026-07-07 13:28:01.563751-06	2026-07-07 13:28:01.563751-06
\N	client.created	clients	12	null	{"legal_name": "ASOCIACION MEXICANA DE INSPECCION DE INFORMACION COMERCIAL AMIIC", "rfc": null, "commercial_name": "ASOCIACION MEXICANA DE INSPECCION DE INFORMACION COMERCIAL AMIIC"}	\N	13	2026-07-07 13:28:01.567517-06	2026-07-07 13:28:01.567517-06
\N	client.created	clients	13	null	{"legal_name": "ASPHALT PAVEMENT & CONSTRUCTION LABORATORIES", "rfc": null, "commercial_name": "ASPHALT PAVEMENT & CONSTRUCTION LABORATORIES"}	\N	14	2026-07-07 13:28:01.571153-06	2026-07-07 13:28:01.571153-06
\N	client.created	clients	14	null	{"legal_name": "ATS", "rfc": null, "commercial_name": "ATS"}	\N	15	2026-07-07 13:28:01.575428-06	2026-07-07 13:28:01.575428-06
\N	client.created	clients	15	null	{"legal_name": "ATS, Josed De Jesus Valdez Roman", "rfc": null, "commercial_name": "ATS, Josed De Jesus Valdez Roman"}	\N	16	2026-07-07 13:28:01.578184-06	2026-07-07 13:28:01.578184-06
\N	client.created	clients	16	null	{"legal_name": "AUDI LOPEZ MATEOS", "rfc": null, "commercial_name": "AUDI LOPEZ MATEOS"}	\N	17	2026-07-07 13:28:01.581637-06	2026-07-07 13:28:01.581637-06
\N	client.created	clients	17	null	{"legal_name": "AUTOCAMIONES DE MEXICO", "rfc": null, "commercial_name": "AUTOCAMIONES DE MEXICO"}	\N	18	2026-07-07 13:28:01.585544-06	2026-07-07 13:28:01.585544-06
\N	client.created	clients	18	null	{"legal_name": "AUTOMOTORES FLOVA", "rfc": null, "commercial_name": "AUTOMOTORES FLOVA"}	\N	19	2026-07-07 13:28:01.589839-06	2026-07-07 13:28:01.589839-06
\N	client.created	clients	19	null	{"legal_name": "AUTONOVA", "rfc": null, "commercial_name": "AUTONOVA"}	\N	20	2026-07-07 13:28:01.592995-06	2026-07-07 13:28:01.592995-06
\N	client.created	clients	20	null	{"legal_name": "AVISAIL FLORES LUNA", "rfc": null, "commercial_name": "AVISAIL FLORES LUNA"}	\N	21	2026-07-07 13:28:01.5957-06	2026-07-07 13:28:01.5957-06
\N	client.created	clients	21	null	{"legal_name": "Adler Pharma, S. de R.L. de C.V.", "rfc": null, "commercial_name": "Adler Pharma, S. de R.L. de C.V."}	\N	22	2026-07-07 13:28:01.599883-06	2026-07-07 13:28:01.599883-06
\N	client.created	clients	22	null	{"legal_name": "Aeroplasa de Occidente, S.A. de C.V.", "rfc": null, "commercial_name": "Aeroplasa de Occidente, S.A. de C.V."}	\N	23	2026-07-07 13:28:01.604491-06	2026-07-07 13:28:01.604491-06
\N	client.created	clients	23	null	{"legal_name": "Agrovet Market M\\u00e9xico", "rfc": null, "commercial_name": "Agrovet Market M\\u00e9xico"}	\N	24	2026-07-07 13:28:01.608484-06	2026-07-07 13:28:01.608484-06
\N	client.created	clients	24	null	{"legal_name": "Alberto Evangelista Placencia", "rfc": null, "commercial_name": "Alberto Evangelista Placencia"}	\N	25	2026-07-07 13:28:01.612334-06	2026-07-07 13:28:01.612334-06
\N	client.created	clients	25	null	{"legal_name": "Allison Rebeca", "rfc": null, "commercial_name": "Allison Rebeca"}	\N	26	2026-07-07 13:28:01.617571-06	2026-07-07 13:28:01.617571-06
\N	client.created	clients	26	null	{"legal_name": "Ambiderm, S.A. de C.V.", "rfc": null, "commercial_name": "Ambiderm, S.A. de C.V."}	\N	27	2026-07-07 13:28:01.621776-06	2026-07-07 13:28:01.621776-06
\N	client.created	clients	27	null	{"legal_name": "American Industries", "rfc": null, "commercial_name": "American Industries"}	\N	28	2026-07-07 13:28:01.624783-06	2026-07-07 13:28:01.624783-06
\N	client.created	clients	28	null	{"legal_name": "Asesores en equipos de proteccion industrial sire", "rfc": null, "commercial_name": "Asesores en equipos de proteccion industrial sire"}	\N	29	2026-07-07 13:28:01.627437-06	2026-07-07 13:28:01.627437-06
\N	client.created	clients	29	null	{"legal_name": "Asiip", "rfc": null, "commercial_name": "Asiip"}	\N	30	2026-07-07 13:28:01.630542-06	2026-07-07 13:28:01.630542-06
\N	client.created	clients	30	null	{"legal_name": "Atisa Mx", "rfc": null, "commercial_name": "Atisa Mx"}	\N	31	2026-07-07 13:28:01.634474-06	2026-07-07 13:28:01.634474-06
\N	client.created	clients	31	null	{"legal_name": "Audi Center Galerias", "rfc": null, "commercial_name": "Audi Center Galerias"}	\N	32	2026-07-07 13:28:01.637731-06	2026-07-07 13:28:01.637731-06
\N	client.created	clients	32	null	{"legal_name": "Audi center patria", "rfc": null, "commercial_name": "Audi center patria"}	\N	33	2026-07-07 13:28:01.64213-06	2026-07-07 13:28:01.64213-06
\N	client.created	clients	33	null	{"legal_name": "Automotriz celaya S.A. DE C.V.", "rfc": null, "commercial_name": "Automotriz celaya S.A. DE C.V."}	\N	34	2026-07-07 13:28:01.645887-06	2026-07-07 13:28:01.645887-06
\N	client.created	clients	34	null	{"legal_name": "BIODESARROLLOS VALMEX", "rfc": null, "commercial_name": "BIODESARROLLOS VALMEX"}	\N	35	2026-07-07 13:28:01.649448-06	2026-07-07 13:28:01.649448-06
\N	client.created	clients	35	null	{"legal_name": "BMC Medical Manufacturing", "rfc": null, "commercial_name": "BMC Medical Manufacturing"}	\N	36	2026-07-07 13:28:01.653692-06	2026-07-07 13:28:01.653692-06
\N	client.created	clients	36	null	{"legal_name": "BONYARD SERVICIOS", "rfc": null, "commercial_name": "BONYARD SERVICIOS"}	\N	37	2026-07-07 13:28:01.657444-06	2026-07-07 13:28:01.657444-06
\N	client.created	clients	37	null	{"legal_name": "BORMANN", "rfc": null, "commercial_name": "BORMANN"}	\N	38	2026-07-07 13:28:01.660126-06	2026-07-07 13:28:01.660126-06
\N	client.created	clients	38	null	{"legal_name": "Begalat pharma", "rfc": null, "commercial_name": "Begalat pharma"}	\N	39	2026-07-07 13:28:01.662623-06	2026-07-07 13:28:01.662623-06
\N	client.created	clients	39	null	{"legal_name": "Betone", "rfc": null, "commercial_name": "Betone"}	\N	40	2026-07-07 13:28:01.6669-06	2026-07-07 13:28:01.6669-06
\N	client.created	clients	40	null	{"legal_name": "Biobest M\\u00e9xico, S.A. de C.V.", "rfc": null, "commercial_name": "Biobest M\\u00e9xico, S.A. de C.V."}	\N	41	2026-07-07 13:28:01.67018-06	2026-07-07 13:28:01.67018-06
\N	client.created	clients	41	null	{"legal_name": "CA&CER Ingenier\\u00eda y Metrolog\\u00eda S.A.S", "rfc": null, "commercial_name": "CA&CER Ingenier\\u00eda y Metrolog\\u00eda S.A.S"}	\N	42	2026-07-07 13:28:01.673308-06	2026-07-07 13:28:01.673308-06
\N	client.created	clients	42	null	{"legal_name": "CAB LOGISTICS", "rfc": null, "commercial_name": "CAB LOGISTICS"}	\N	43	2026-07-07 13:28:01.677225-06	2026-07-07 13:28:01.677225-06
\N	client.created	clients	46	null	{"legal_name": "CEMSI (SERVICIO DE MANTENIMIENTO)", "rfc": null, "commercial_name": "CEMSI (SERVICIO DE MANTENIMIENTO)"}	\N	47	2026-07-07 13:28:01.692063-06	2026-07-07 13:28:01.692063-06
\N	client.created	clients	50	null	{"legal_name": "CFE", "rfc": null, "commercial_name": "CFE"}	\N	51	2026-07-07 13:28:01.702605-06	2026-07-07 13:28:01.702605-06
\N	client.created	clients	54	null	{"legal_name": "CONCRETOS DCC", "rfc": null, "commercial_name": "CONCRETOS DCC"}	\N	55	2026-07-07 13:28:01.714114-06	2026-07-07 13:28:01.714114-06
\N	client.created	clients	58	null	{"legal_name": "CONSIGUELO", "rfc": null, "commercial_name": "CONSIGUELO"}	\N	59	2026-07-07 13:28:01.725061-06	2026-07-07 13:28:01.725061-06
\N	client.created	clients	62	null	{"legal_name": "CORRUGADOS HEAVY BOX", "rfc": null, "commercial_name": "CORRUGADOS HEAVY BOX"}	\N	63	2026-07-07 13:28:01.735783-06	2026-07-07 13:28:01.735783-06
\N	client.created	clients	66	null	{"legal_name": "Calibraciones e Inspecciones CEISA", "rfc": null, "commercial_name": "Calibraciones e Inspecciones CEISA"}	\N	67	2026-07-07 13:28:01.747501-06	2026-07-07 13:28:01.747501-06
\N	client.created	clients	70	null	{"legal_name": "Capymet", "rfc": null, "commercial_name": "Capymet"}	\N	71	2026-07-07 13:28:01.759249-06	2026-07-07 13:28:01.759249-06
\N	client.created	clients	74	null	{"legal_name": "Casa Tradici\\u00f3n, Boga de Jesus Mu\\u00f1iz Gomez", "rfc": null, "commercial_name": "Casa Tradici\\u00f3n, Boga de Jesus Mu\\u00f1iz Gomez"}	\N	75	2026-07-07 13:28:01.769513-06	2026-07-07 13:28:01.769513-06
\N	client.created	clients	78	null	{"legal_name": "Cohmedic, S.A. de C.V.", "rfc": null, "commercial_name": "Cohmedic, S.A. de C.V."}	\N	79	2026-07-07 13:28:01.782072-06	2026-07-07 13:28:01.782072-06
\N	client.created	clients	82	null	{"legal_name": "Comercializadora Flexible, S.A. de C.V.", "rfc": null, "commercial_name": "Comercializadora Flexible, S.A. de C.V."}	\N	83	2026-07-07 13:28:01.792654-06	2026-07-07 13:28:01.792654-06
\N	client.created	clients	86	null	{"legal_name": "Consocio Valsi", "rfc": null, "commercial_name": "Consocio Valsi"}	\N	87	2026-07-07 13:28:01.80476-06	2026-07-07 13:28:01.80476-06
\N	client.created	clients	90	null	{"legal_name": "Craf.", "rfc": null, "commercial_name": "Craf."}	\N	91	2026-07-07 13:28:01.816173-06	2026-07-07 13:28:01.816173-06
\N	client.created	clients	94	null	{"legal_name": "Distribuidora Volkswagen Central, S.A. de C.V.", "rfc": null, "commercial_name": "Distribuidora Volkswagen Central, S.A. de C.V."}	\N	95	2026-07-07 13:28:01.827542-06	2026-07-07 13:28:01.827542-06
\N	client.created	clients	98	null	{"legal_name": "EURO STERN", "rfc": null, "commercial_name": "EURO STERN"}	\N	99	2026-07-07 13:28:01.836892-06	2026-07-07 13:28:01.836892-06
\N	client.created	clients	102	null	{"legal_name": "Electromedica Tinajero", "rfc": null, "commercial_name": "Electromedica Tinajero"}	\N	103	2026-07-07 13:28:01.846499-06	2026-07-07 13:28:01.846499-06
\N	client.created	clients	106	null	{"legal_name": "Eurostern Country", "rfc": null, "commercial_name": "Eurostern Country"}	\N	107	2026-07-07 13:28:01.856444-06	2026-07-07 13:28:01.856444-06
\N	client.created	clients	110	null	{"legal_name": "FARMACIA SANTIAGO-BARAJAS", "rfc": null, "commercial_name": "FARMACIA SANTIAGO-BARAJAS"}	\N	111	2026-07-07 13:28:01.868876-06	2026-07-07 13:28:01.868876-06
\N	client.created	clients	114	null	{"legal_name": "FGR Transformaciones Met\\u00e1licas, S.A. de C.V.", "rfc": null, "commercial_name": "FGR Transformaciones Met\\u00e1licas, S.A. de C.V."}	\N	115	2026-07-07 13:28:01.879155-06	2026-07-07 13:28:01.879155-06
\N	client.created	clients	118	null	{"legal_name": "FM INGENIEROS", "rfc": null, "commercial_name": "FM INGENIEROS"}	\N	119	2026-07-07 13:28:01.888987-06	2026-07-07 13:28:01.888987-06
\N	client.created	clients	122	null	{"legal_name": "FTECH", "rfc": null, "commercial_name": "FTECH"}	\N	123	2026-07-07 13:28:01.898032-06	2026-07-07 13:28:01.898032-06
\N	client.created	clients	126	null	{"legal_name": "Firexpro de M\\u00e9xico, S. de R.L. de C.V.", "rfc": null, "commercial_name": "Firexpro de M\\u00e9xico, S. de R.L. de C.V."}	\N	127	2026-07-07 13:28:01.908823-06	2026-07-07 13:28:01.908823-06
\N	client.created	clients	130	null	{"legal_name": "Food Microbiology Laboratories, Cristian Juarez", "rfc": null, "commercial_name": "Food Microbiology Laboratories, Cristian Juarez"}	\N	131	2026-07-07 13:28:01.918472-06	2026-07-07 13:28:01.918472-06
\N	client.created	clients	134	null	{"legal_name": "Francisco Javier Ordaz Higareda", "rfc": null, "commercial_name": "Francisco Javier Ordaz Higareda"}	\N	135	2026-07-07 13:28:01.928866-06	2026-07-07 13:28:01.928866-06
\N	client.created	clients	138	null	{"legal_name": "GRUPO AGC", "rfc": null, "commercial_name": "GRUPO AGC"}	\N	139	2026-07-07 13:28:01.939308-06	2026-07-07 13:28:01.939308-06
\N	client.created	clients	142	null	{"legal_name": "Gloria Leon Murillo", "rfc": null, "commercial_name": "Gloria Leon Murillo"}	\N	143	2026-07-07 13:28:01.947065-06	2026-07-07 13:28:01.947065-06
\N	client.created	clients	146	null	{"legal_name": "Grupo Collado", "rfc": null, "commercial_name": "Grupo Collado"}	\N	147	2026-07-07 13:28:01.955943-06	2026-07-07 13:28:01.955943-06
\N	client.created	clients	150	null	{"legal_name": "HARD ROCK HOTEL GUADALAJARA", "rfc": null, "commercial_name": "HARD ROCK HOTEL GUADALAJARA"}	\N	151	2026-07-07 13:28:01.964003-06	2026-07-07 13:28:01.964003-06
\N	client.created	clients	154	null	{"legal_name": "HULPAC", "rfc": null, "commercial_name": "HULPAC"}	\N	155	2026-07-07 13:28:01.973096-06	2026-07-07 13:28:01.973096-06
\N	client.created	clients	158	null	{"legal_name": "Hennigues Automotive", "rfc": null, "commercial_name": "Hennigues Automotive"}	\N	159	2026-07-07 13:28:01.981632-06	2026-07-07 13:28:01.981632-06
\N	client.created	clients	162	null	{"legal_name": "Hospital Santa Margarita, S.A. de C.V.", "rfc": null, "commercial_name": "Hospital Santa Margarita, S.A. de C.V."}	\N	163	2026-07-07 13:28:01.990749-06	2026-07-07 13:28:01.990749-06
\N	client.created	clients	166	null	{"legal_name": "IGNIS Servicios", "rfc": null, "commercial_name": "IGNIS Servicios"}	\N	167	2026-07-07 13:28:01.998755-06	2026-07-07 13:28:01.998755-06
\N	client.created	clients	170	null	{"legal_name": "INDORAMA VENTURES", "rfc": null, "commercial_name": "INDORAMA VENTURES"}	\N	171	2026-07-07 13:28:02.007927-06	2026-07-07 13:28:02.007927-06
\N	client.created	clients	174	null	{"legal_name": "INGRASYS TECHNOLOGY MEXICO", "rfc": null, "commercial_name": "INGRASYS TECHNOLOGY MEXICO"}	\N	175	2026-07-07 13:28:02.015577-06	2026-07-07 13:28:02.015577-06
\N	client.created	clients	178	null	{"legal_name": "IPRODISA", "rfc": null, "commercial_name": "IPRODISA"}	\N	179	2026-07-07 13:28:02.024708-06	2026-07-07 13:28:02.024708-06
\N	client.created	clients	182	null	{"legal_name": "Ingenieria Proyectos y Dise\\u00f1os", "rfc": null, "commercial_name": "Ingenieria Proyectos y Dise\\u00f1os"}	\N	183	2026-07-07 13:28:02.031562-06	2026-07-07 13:28:02.031562-06
\N	client.created	clients	186	null	{"legal_name": "Itesvia de Mexico S.A. de C.V.", "rfc": null, "commercial_name": "Itesvia de Mexico S.A. de C.V."}	\N	187	2026-07-07 13:28:02.040703-06	2026-07-07 13:28:02.040703-06
\N	client.created	clients	190	null	{"legal_name": "JUAN PABLO MENDOZA ROMAN", "rfc": null, "commercial_name": "JUAN PABLO MENDOZA ROMAN"}	\N	191	2026-07-07 13:28:02.050357-06	2026-07-07 13:28:02.050357-06
\N	client.created	clients	194	null	{"legal_name": "Jose Mar\\u00eda Godinez Enriquez", "rfc": null, "commercial_name": "Jose Mar\\u00eda Godinez Enriquez"}	\N	195	2026-07-07 13:28:02.057845-06	2026-07-07 13:28:02.057845-06
\N	client.created	clients	198	null	{"legal_name": "LA FARMACIA DROGUER\\u00cdA", "rfc": null, "commercial_name": "LA FARMACIA DROGUER\\u00cdA"}	\N	199	2026-07-07 13:28:02.065259-06	2026-07-07 13:28:02.065259-06
\N	client.created	clients	202	null	{"legal_name": "LEONARDO AGUILAR LERMA", "rfc": null, "commercial_name": "LEONARDO AGUILAR LERMA"}	\N	203	2026-07-07 13:28:02.073274-06	2026-07-07 13:28:02.073274-06
\N	client.created	clients	208	null	{"legal_name": "La Empresa de los Cien A\\u00f1os", "rfc": null, "commercial_name": "La Empresa de los Cien A\\u00f1os"}	\N	209	2026-07-07 13:28:02.084115-06	2026-07-07 13:28:02.084115-06
\N	client.created	clients	43	null	{"legal_name": "CAFISON", "rfc": null, "commercial_name": "CAFISON"}	\N	44	2026-07-07 13:28:01.680802-06	2026-07-07 13:28:01.680802-06
\N	client.created	clients	47	null	{"legal_name": "CENTRO DE DESARROLLO EN INSTRUMENTACION Y CAPACITACION", "rfc": null, "commercial_name": "CENTRO DE DESARROLLO EN INSTRUMENTACION Y CAPACITACION"}	\N	48	2026-07-07 13:28:01.694342-06	2026-07-07 13:28:01.694342-06
\N	client.created	clients	51	null	{"legal_name": "CHUPALETAS S.A. DE C.V.", "rfc": null, "commercial_name": "CHUPALETAS S.A. DE C.V."}	\N	52	2026-07-07 13:28:01.706478-06	2026-07-07 13:28:01.706478-06
\N	client.created	clients	55	null	{"legal_name": "CONCRETOS LANZADOS CONSTRUCCIONES", "rfc": null, "commercial_name": "CONCRETOS LANZADOS CONSTRUCCIONES"}	\N	56	2026-07-07 13:28:01.716951-06	2026-07-07 13:28:01.716951-06
\N	client.created	clients	59	null	{"legal_name": "CONSULTEC SRV", "rfc": null, "commercial_name": "CONSULTEC SRV"}	\N	60	2026-07-07 13:28:01.72743-06	2026-07-07 13:28:01.72743-06
\N	client.created	clients	63	null	{"legal_name": "CRAFT AV\\u00cdA CENTER", "rfc": null, "commercial_name": "CRAFT AV\\u00cdA CENTER"}	\N	64	2026-07-07 13:28:01.738554-06	2026-07-07 13:28:01.738554-06
\N	client.created	clients	67	null	{"legal_name": "Calkins Burke and Zannie de M\\u00e9xico, S.A. de C.V.", "rfc": null, "commercial_name": "Calkins Burke and Zannie de M\\u00e9xico, S.A. de C.V."}	\N	68	2026-07-07 13:28:01.751015-06	2026-07-07 13:28:01.751015-06
\N	client.created	clients	71	null	{"legal_name": "Carbotecnia, S.A. de C.V.", "rfc": null, "commercial_name": "Carbotecnia, S.A. de C.V."}	\N	72	2026-07-07 13:28:01.761594-06	2026-07-07 13:28:01.761594-06
\N	client.created	clients	75	null	{"legal_name": "Centro de Metrolog\\u00eda Ingenier\\u00eda e Innovaci\\u00f3n", "rfc": null, "commercial_name": "Centro de Metrolog\\u00eda Ingenier\\u00eda e Innovaci\\u00f3n"}	\N	76	2026-07-07 13:28:01.772403-06	2026-07-07 13:28:01.772403-06
\N	client.created	clients	79	null	{"legal_name": "Collins Divisi\\u00f3n Veterinaria", "rfc": null, "commercial_name": "Collins Divisi\\u00f3n Veterinaria"}	\N	80	2026-07-07 13:28:01.785406-06	2026-07-07 13:28:01.785406-06
\N	client.created	clients	83	null	{"legal_name": "Comercializadora Gonac, S.A. de C.V.", "rfc": null, "commercial_name": "Comercializadora Gonac, S.A. de C.V."}	\N	84	2026-07-07 13:28:01.794742-06	2026-07-07 13:28:01.794742-06
\N	client.created	clients	87	null	{"legal_name": "Construcciones e Ingenier\\u00eda Especializada del Norte, S.A. de C.V.", "rfc": null, "commercial_name": "Construcciones e Ingenier\\u00eda Especializada del Norte, S.A. de C.V."}	\N	88	2026-07-07 13:28:01.807398-06	2026-07-07 13:28:01.807398-06
\N	client.created	clients	91	null	{"legal_name": "DISTRIBUIDORA DE EQUIPO MEDICO INDSUTRIAL DE M\\u00c9XICO", "rfc": null, "commercial_name": "DISTRIBUIDORA DE EQUIPO MEDICO INDSUTRIAL DE M\\u00c9XICO"}	\N	92	2026-07-07 13:28:01.819135-06	2026-07-07 13:28:01.819135-06
\N	client.created	clients	95	null	{"legal_name": "EATON BUSSMANN S DE RL DE CV", "rfc": null, "commercial_name": "EATON BUSSMANN S DE RL DE CV"}	\N	96	2026-07-07 13:28:01.829715-06	2026-07-07 13:28:01.829715-06
\N	client.created	clients	99	null	{"legal_name": "Eagle Ice Fruit, S.A. de C.V.", "rfc": null, "commercial_name": "Eagle Ice Fruit, S.A. de C.V."}	\N	100	2026-07-07 13:28:01.840056-06	2026-07-07 13:28:01.840056-06
\N	client.created	clients	103	null	{"legal_name": "Elevadores Fergar, S.A. de C.V.", "rfc": null, "commercial_name": "Elevadores Fergar, S.A. de C.V."}	\N	104	2026-07-07 13:28:01.84886-06	2026-07-07 13:28:01.84886-06
\N	client.created	clients	107	null	{"legal_name": "Exportaciones Zepeda", "rfc": null, "commercial_name": "Exportaciones Zepeda"}	\N	108	2026-07-07 13:28:01.859948-06	2026-07-07 13:28:01.859948-06
\N	client.created	clients	111	null	{"legal_name": "FERMIN ZU\\u00d1IGA DIAZ", "rfc": null, "commercial_name": "FERMIN ZU\\u00d1IGA DIAZ"}	\N	112	2026-07-07 13:28:01.87143-06	2026-07-07 13:28:01.87143-06
\N	client.created	clients	115	null	{"legal_name": "FISCALIA GENERAL COLIMA", "rfc": null, "commercial_name": "FISCALIA GENERAL COLIMA"}	\N	116	2026-07-07 13:28:01.881452-06	2026-07-07 13:28:01.881452-06
\N	client.created	clients	119	null	{"legal_name": "FR TERMINALES", "rfc": null, "commercial_name": "FR TERMINALES"}	\N	120	2026-07-07 13:28:01.891443-06	2026-07-07 13:28:01.891443-06
\N	client.created	clients	123	null	{"legal_name": "Fabrica de Cajas y Empaques La Providencia", "rfc": null, "commercial_name": "Fabrica de Cajas y Empaques La Providencia"}	\N	124	2026-07-07 13:28:01.900984-06	2026-07-07 13:28:01.900984-06
\N	client.created	clients	127	null	{"legal_name": "Flosol Eulogio Parra", "rfc": null, "commercial_name": "Flosol Eulogio Parra"}	\N	128	2026-07-07 13:28:01.911102-06	2026-07-07 13:28:01.911102-06
\N	client.created	clients	131	null	{"legal_name": "Food Microbiology Laboratories, Nancy Ramirez", "rfc": null, "commercial_name": "Food Microbiology Laboratories, Nancy Ramirez"}	\N	132	2026-07-07 13:28:01.92103-06	2026-07-07 13:28:01.92103-06
\N	client.created	clients	135	null	{"legal_name": "GAMI INGENIERIA E INSTALACIONES", "rfc": null, "commercial_name": "GAMI INGENIERIA E INSTALACIONES"}	\N	136	2026-07-07 13:28:01.931464-06	2026-07-07 13:28:01.931464-06
\N	client.created	clients	139	null	{"legal_name": "GUADALUPE MONSERRAT ARCE CORTES", "rfc": null, "commercial_name": "GUADALUPE MONSERRAT ARCE CORTES"}	\N	140	2026-07-07 13:28:01.941555-06	2026-07-07 13:28:01.941555-06
\N	client.created	clients	143	null	{"legal_name": "Grupo Alferelectric, S.A. de C.V.", "rfc": null, "commercial_name": "Grupo Alferelectric, S.A. de C.V."}	\N	144	2026-07-07 13:28:01.949001-06	2026-07-07 13:28:01.949001-06
\N	client.created	clients	147	null	{"legal_name": "Grupo Excala", "rfc": null, "commercial_name": "Grupo Excala"}	\N	148	2026-07-07 13:28:01.958443-06	2026-07-07 13:28:01.958443-06
\N	client.created	clients	151	null	{"legal_name": "HENIGGUES AUTOMOTIVE", "rfc": null, "commercial_name": "HENIGGUES AUTOMOTIVE"}	\N	152	2026-07-07 13:28:01.966277-06	2026-07-07 13:28:01.966277-06
\N	client.created	clients	155	null	{"legal_name": "Hacienda la", "rfc": null, "commercial_name": "Hacienda la"}	\N	156	2026-07-07 13:28:01.975253-06	2026-07-07 13:28:01.975253-06
\N	client.created	clients	159	null	{"legal_name": "Hidrom\\u00f3vil, S.A. de C.V.", "rfc": null, "commercial_name": "Hidrom\\u00f3vil, S.A. de C.V."}	\N	160	2026-07-07 13:28:01.983905-06	2026-07-07 13:28:01.983905-06
\N	client.created	clients	163	null	{"legal_name": "IB PACK", "rfc": null, "commercial_name": "IB PACK"}	\N	164	2026-07-07 13:28:01.993029-06	2026-07-07 13:28:01.993029-06
\N	client.created	clients	167	null	{"legal_name": "IMPULSORA INDUSTRIAL DE REFRIGERACION", "rfc": null, "commercial_name": "IMPULSORA INDUSTRIAL DE REFRIGERACION"}	\N	168	2026-07-07 13:28:02.000877-06	2026-07-07 13:28:02.000877-06
\N	client.created	clients	171	null	{"legal_name": "INDUSTRIAL DEVELOPMENT, CONTROL AND INSTRUMENTS", "rfc": null, "commercial_name": "INDUSTRIAL DEVELOPMENT, CONTROL AND INSTRUMENTS"}	\N	172	2026-07-07 13:28:02.009665-06	2026-07-07 13:28:02.009665-06
\N	client.created	clients	175	null	{"legal_name": "INNOVACIONES FELWE", "rfc": null, "commercial_name": "INNOVACIONES FELWE"}	\N	176	2026-07-07 13:28:02.017909-06	2026-07-07 13:28:02.017909-06
\N	client.created	clients	179	null	{"legal_name": "IVAN JESUS LOPEZ MERTINEZ", "rfc": null, "commercial_name": "IVAN JESUS LOPEZ MERTINEZ"}	\N	180	2026-07-07 13:28:02.026384-06	2026-07-07 13:28:02.026384-06
\N	client.created	clients	183	null	{"legal_name": "Insofos, S.A.P.I. de C.V.", "rfc": null, "commercial_name": "Insofos, S.A.P.I. de C.V."}	\N	184	2026-07-07 13:28:02.033788-06	2026-07-07 13:28:02.033788-06
\N	client.created	clients	187	null	{"legal_name": "JANETH PARRAL PLASCENCIA", "rfc": null, "commercial_name": "JANETH PARRAL PLASCENCIA"}	\N	188	2026-07-07 13:28:02.043161-06	2026-07-07 13:28:02.043161-06
\N	client.created	clients	191	null	{"legal_name": "Jimena Garcia Alonso", "rfc": null, "commercial_name": "Jimena Garcia Alonso"}	\N	192	2026-07-07 13:28:02.052144-06	2026-07-07 13:28:02.052144-06
\N	client.created	clients	195	null	{"legal_name": "Juan Pablo Mart\\u00ednez Moreno", "rfc": null, "commercial_name": "Juan Pablo Mart\\u00ednez Moreno"}	\N	196	2026-07-07 13:28:02.059454-06	2026-07-07 13:28:02.059454-06
\N	client.created	clients	44	null	{"legal_name": "CALIBRACIONES E INSTRUMENTOS", "rfc": null, "commercial_name": "CALIBRACIONES E INSTRUMENTOS"}	\N	45	2026-07-07 13:28:01.68445-06	2026-07-07 13:28:01.68445-06
\N	client.created	clients	48	null	{"legal_name": "CENTRO DE METROLOG\\u00cdA JUVA", "rfc": null, "commercial_name": "CENTRO DE METROLOG\\u00cdA JUVA"}	\N	49	2026-07-07 13:28:01.69696-06	2026-07-07 13:28:01.69696-06
\N	client.created	clients	52	null	{"legal_name": "CMC METROLOGY", "rfc": null, "commercial_name": "CMC METROLOGY"}	\N	53	2026-07-07 13:28:01.708984-06	2026-07-07 13:28:01.708984-06
\N	client.created	clients	56	null	{"legal_name": "CONEXIONES", "rfc": null, "commercial_name": "CONEXIONES"}	\N	57	2026-07-07 13:28:01.719887-06	2026-07-07 13:28:01.719887-06
\N	client.created	clients	60	null	{"legal_name": "CONSULTOR\\u00cdA BIOMEDICA INTEGRAL", "rfc": null, "commercial_name": "CONSULTOR\\u00cdA BIOMEDICA INTEGRAL"}	\N	61	2026-07-07 13:28:01.729695-06	2026-07-07 13:28:01.729695-06
\N	client.created	clients	64	null	{"legal_name": "CRG PROYECTOS Y MANTENIMIENTO INDUSTRIAL DE LOS ALTOS", "rfc": null, "commercial_name": "CRG PROYECTOS Y MANTENIMIENTO INDUSTRIAL DE LOS ALTOS"}	\N	65	2026-07-07 13:28:01.741903-06	2026-07-07 13:28:01.741903-06
\N	client.created	clients	68	null	{"legal_name": "Calza Garver, S.A. de C.V.", "rfc": null, "commercial_name": "Calza Garver, S.A. de C.V."}	\N	69	2026-07-07 13:28:01.753803-06	2026-07-07 13:28:01.753803-06
\N	client.created	clients	72	null	{"legal_name": "Casa Tradici\\u00f3n", "rfc": null, "commercial_name": "Casa Tradici\\u00f3n"}	\N	73	2026-07-07 13:28:01.763778-06	2026-07-07 13:28:01.763778-06
\N	client.created	clients	76	null	{"legal_name": "Cepi Especialistas en Proyectos contra Incendio, S.A. de C.V.", "rfc": null, "commercial_name": "Cepi Especialistas en Proyectos contra Incendio, S.A. de C.V."}	\N	77	2026-07-07 13:28:01.776282-06	2026-07-07 13:28:01.776282-06
\N	client.created	clients	80	null	{"legal_name": "Comercial Automotriz del Noroeste S.A. de C.V.", "rfc": null, "commercial_name": "Comercial Automotriz del Noroeste S.A. de C.V."}	\N	81	2026-07-07 13:28:01.78789-06	2026-07-07 13:28:01.78789-06
\N	client.created	clients	84	null	{"legal_name": "comintec", "rfc": null, "commercial_name": "comintec"}	\N	85	2026-07-07 13:28:01.798304-06	2026-07-07 13:28:01.798304-06
\N	client.created	clients	88	null	{"legal_name": "Consultoria biomedica Integral", "rfc": null, "commercial_name": "Consultoria biomedica Integral"}	\N	89	2026-07-07 13:28:01.810334-06	2026-07-07 13:28:01.810334-06
\N	client.created	clients	92	null	{"legal_name": "DULYMEX", "rfc": null, "commercial_name": "DULYMEX"}	\N	93	2026-07-07 13:28:01.821976-06	2026-07-07 13:28:01.821976-06
\N	client.created	clients	96	null	{"legal_name": "ELECTRIC ADVANCE", "rfc": null, "commercial_name": "ELECTRIC ADVANCE"}	\N	97	2026-07-07 13:28:01.831815-06	2026-07-07 13:28:01.831815-06
\N	client.created	clients	100	null	{"legal_name": "Ecochillers Corporation, S.A. de C.V.", "rfc": null, "commercial_name": "Ecochillers Corporation, S.A. de C.V."}	\N	101	2026-07-07 13:28:01.842328-06	2026-07-07 13:28:01.842328-06
\N	client.created	clients	104	null	{"legal_name": "Erika Valencia", "rfc": null, "commercial_name": "Erika Valencia"}	\N	105	2026-07-07 13:28:01.851541-06	2026-07-07 13:28:01.851541-06
\N	client.created	clients	108	null	{"legal_name": "FANOSA SA DE CV", "rfc": null, "commercial_name": "FANOSA SA DE CV"}	\N	109	2026-07-07 13:28:01.862716-06	2026-07-07 13:28:01.862716-06
\N	client.created	clients	112	null	{"legal_name": "FERRETERIA INDUSTRIAL ARENAS", "rfc": null, "commercial_name": "FERRETERIA INDUSTRIAL ARENAS"}	\N	113	2026-07-07 13:28:01.873946-06	2026-07-07 13:28:01.873946-06
\N	client.created	clients	116	null	{"legal_name": "FISCALIA GENERAL DE LA REPUBLICA", "rfc": null, "commercial_name": "FISCALIA GENERAL DE LA REPUBLICA"}	\N	117	2026-07-07 13:28:01.883952-06	2026-07-07 13:28:01.883952-06
\N	client.created	clients	120	null	{"legal_name": "FRESHCOURT", "rfc": null, "commercial_name": "FRESHCOURT"}	\N	121	2026-07-07 13:28:01.893709-06	2026-07-07 13:28:01.893709-06
\N	client.created	clients	124	null	{"legal_name": "Fabricaci\\u00f3n y manofactura de perfiles", "rfc": null, "commercial_name": "Fabricaci\\u00f3n y manofactura de perfiles"}	\N	125	2026-07-07 13:28:01.903861-06	2026-07-07 13:28:01.903861-06
\N	client.created	clients	128	null	{"legal_name": "Flosol Motors S.A. de C.V.", "rfc": null, "commercial_name": "Flosol Motors S.A. de C.V."}	\N	129	2026-07-07 13:28:01.913047-06	2026-07-07 13:28:01.913047-06
\N	client.created	clients	132	null	{"legal_name": "Foxconn", "rfc": null, "commercial_name": "Foxconn"}	\N	133	2026-07-07 13:28:01.923572-06	2026-07-07 13:28:01.923572-06
\N	client.created	clients	136	null	{"legal_name": "GENERAL BRANDS MANOFACTURAS MEXICO", "rfc": null, "commercial_name": "GENERAL BRANDS MANOFACTURAS MEXICO"}	\N	137	2026-07-07 13:28:01.933947-06	2026-07-07 13:28:01.933947-06
\N	client.created	clients	140	null	{"legal_name": "General Electric", "rfc": null, "commercial_name": "General Electric"}	\N	141	2026-07-07 13:28:01.943445-06	2026-07-07 13:28:01.943445-06
\N	client.created	clients	144	null	{"legal_name": "Grupo CPQ", "rfc": null, "commercial_name": "Grupo CPQ"}	\N	145	2026-07-07 13:28:01.951746-06	2026-07-07 13:28:01.951746-06
\N	client.created	clients	148	null	{"legal_name": "Gustinos", "rfc": null, "commercial_name": "Gustinos"}	\N	149	2026-07-07 13:28:01.960586-06	2026-07-07 13:28:01.960586-06
\N	client.created	clients	152	null	{"legal_name": "HERRAMIENTAS INDUSTRIALES GDL, S.A. de C.V.", "rfc": null, "commercial_name": "HERRAMIENTAS INDUSTRIALES GDL, S.A. de C.V."}	\N	153	2026-07-07 13:28:01.968483-06	2026-07-07 13:28:01.968483-06
\N	client.created	clients	156	null	{"legal_name": "Hector Alejandro Ovalle Rendon", "rfc": null, "commercial_name": "Hector Alejandro Ovalle Rendon"}	\N	157	2026-07-07 13:28:01.977213-06	2026-07-07 13:28:01.977213-06
\N	client.created	clients	160	null	{"legal_name": "Honda de M\\u00e9xico, S.A. de C.V.", "rfc": null, "commercial_name": "Honda de M\\u00e9xico, S.A. de C.V."}	\N	161	2026-07-07 13:28:01.986045-06	2026-07-07 13:28:01.986045-06
\N	client.created	clients	164	null	{"legal_name": "IDSSA TECHNOLOGIES", "rfc": null, "commercial_name": "IDSSA TECHNOLOGIES"}	\N	165	2026-07-07 13:28:01.995252-06	2026-07-07 13:28:01.995252-06
\N	client.created	clients	168	null	{"legal_name": "INALFA", "rfc": null, "commercial_name": "INALFA"}	\N	169	2026-07-07 13:28:02.003147-06	2026-07-07 13:28:02.003147-06
\N	client.created	clients	172	null	{"legal_name": "INDUSTRIAS CABRERA", "rfc": null, "commercial_name": "INDUSTRIAS CABRERA"}	\N	173	2026-07-07 13:28:02.011738-06	2026-07-07 13:28:02.011738-06
\N	client.created	clients	176	null	{"legal_name": "INNOVARE", "rfc": null, "commercial_name": "INNOVARE"}	\N	177	2026-07-07 13:28:02.019949-06	2026-07-07 13:28:02.019949-06
\N	client.created	clients	180	null	{"legal_name": "IZUSU", "rfc": null, "commercial_name": "IZUSU"}	\N	181	2026-07-07 13:28:02.027984-06	2026-07-07 13:28:02.027984-06
\N	client.created	clients	184	null	{"legal_name": "Instalaciones y Mantenimiento de Calidad, S.A. de C.V.", "rfc": null, "commercial_name": "Instalaciones y Mantenimiento de Calidad, S.A. de C.V."}	\N	185	2026-07-07 13:28:02.036413-06	2026-07-07 13:28:02.036413-06
\N	client.created	clients	188	null	{"legal_name": "JORGE GALLO", "rfc": null, "commercial_name": "JORGE GALLO"}	\N	189	2026-07-07 13:28:02.045697-06	2026-07-07 13:28:02.045697-06
\N	client.created	clients	192	null	{"legal_name": "Johnson Electric Group M\\u00e9xico, S. de R.L. de C.V.", "rfc": null, "commercial_name": "Johnson Electric Group M\\u00e9xico, S. de R.L. de C.V."}	\N	193	2026-07-07 13:28:02.054085-06	2026-07-07 13:28:02.054085-06
\N	client.created	clients	196	null	{"legal_name": "KANDYCO", "rfc": null, "commercial_name": "KANDYCO"}	\N	197	2026-07-07 13:28:02.061169-06	2026-07-07 13:28:02.061169-06
\N	client.created	clients	200	null	{"legal_name": "LAYCER", "rfc": null, "commercial_name": "LAYCER"}	\N	201	2026-07-07 13:28:02.068767-06	2026-07-07 13:28:02.068767-06
\N	client.created	clients	204	null	{"legal_name": "LOES INGENIEROS", "rfc": null, "commercial_name": "LOES INGENIEROS"}	\N	205	2026-07-07 13:28:02.077102-06	2026-07-07 13:28:02.077102-06
\N	client.created	clients	366	null	{"legal_name": "henni", "rfc": null, "commercial_name": "henni"}	\N	367	2026-07-07 13:28:02.441955-06	2026-07-07 13:28:02.441955-06
\N	client.created	clients	45	null	{"legal_name": "CAPYMETRO", "rfc": null, "commercial_name": "CAPYMETRO"}	\N	46	2026-07-07 13:28:01.689-06	2026-07-07 13:28:01.689-06
\N	client.created	clients	49	null	{"legal_name": "CENTRO LECHERO COOPERATIVO DE LOS ALTOS", "rfc": null, "commercial_name": "CENTRO LECHERO COOPERATIVO DE LOS ALTOS"}	\N	50	2026-07-07 13:28:01.699714-06	2026-07-07 13:28:01.699714-06
\N	client.created	clients	53	null	{"legal_name": "CONCRETOS CAYACAL", "rfc": null, "commercial_name": "CONCRETOS CAYACAL"}	\N	54	2026-07-07 13:28:01.711356-06	2026-07-07 13:28:01.711356-06
\N	client.created	clients	57	null	{"legal_name": "CONEXIONES INDUSTRIALES DE OCCIDENTE", "rfc": null, "commercial_name": "CONEXIONES INDUSTRIALES DE OCCIDENTE"}	\N	58	2026-07-07 13:28:01.722542-06	2026-07-07 13:28:01.722542-06
\N	client.created	clients	61	null	{"legal_name": "CORPORATIVO GRUPO MEXLAB S.A. DE C.V.", "rfc": null, "commercial_name": "CORPORATIVO GRUPO MEXLAB S.A. DE C.V."}	\N	62	2026-07-07 13:28:01.732486-06	2026-07-07 13:28:01.732486-06
\N	client.created	clients	65	null	{"legal_name": "CUPER BIOSCIENCES", "rfc": null, "commercial_name": "CUPER BIOSCIENCES"}	\N	66	2026-07-07 13:28:01.744335-06	2026-07-07 13:28:01.744335-06
\N	client.created	clients	69	null	{"legal_name": "Calza Sider", "rfc": null, "commercial_name": "Calza Sider"}	\N	70	2026-07-07 13:28:01.756465-06	2026-07-07 13:28:01.756465-06
\N	client.created	clients	73	null	{"legal_name": "Casa Tradici\\u00f3n Sa De Cv, Veronica Guzman", "rfc": null, "commercial_name": "Casa Tradici\\u00f3n Sa De Cv, Veronica Guzman"}	\N	74	2026-07-07 13:28:01.766283-06	2026-07-07 13:28:01.766283-06
\N	client.created	clients	77	null	{"legal_name": "Cierres Autom\\u00e1ticos National, S.A. de C.V.", "rfc": null, "commercial_name": "Cierres Autom\\u00e1ticos National, S.A. de C.V."}	\N	78	2026-07-07 13:28:01.778983-06	2026-07-07 13:28:01.778983-06
\N	client.created	clients	81	null	{"legal_name": "Comercializadora Ferretera Mtz, S.A. de C.V.", "rfc": null, "commercial_name": "Comercializadora Ferretera Mtz, S.A. de C.V."}	\N	82	2026-07-07 13:28:01.790407-06	2026-07-07 13:28:01.790407-06
\N	client.created	clients	85	null	{"legal_name": "Compa\\u00f1\\u00eda Tequilera Hacienda la Capilla, S.A. de C.V", "rfc": null, "commercial_name": "Compa\\u00f1\\u00eda Tequilera Hacienda la Capilla, S.A. de C.V"}	\N	86	2026-07-07 13:28:01.801976-06	2026-07-07 13:28:01.801976-06
\N	client.created	clients	89	null	{"legal_name": "Coventry Bg S.A. de C.V.", "rfc": null, "commercial_name": "Coventry Bg S.A. de C.V."}	\N	90	2026-07-07 13:28:01.813312-06	2026-07-07 13:28:01.813312-06
\N	client.created	clients	93	null	{"legal_name": "Deprag M\\u00e9xico, S. de R.L. de C.V.", "rfc": null, "commercial_name": "Deprag M\\u00e9xico, S. de R.L. de C.V."}	\N	94	2026-07-07 13:28:01.824664-06	2026-07-07 13:28:01.824664-06
\N	client.created	clients	97	null	{"legal_name": "EQUIPOS Y BASCULAS INDUSTRIALES", "rfc": null, "commercial_name": "EQUIPOS Y BASCULAS INDUSTRIALES"}	\N	98	2026-07-07 13:28:01.834456-06	2026-07-07 13:28:01.834456-06
\N	client.created	clients	101	null	{"legal_name": "Electroconstrucciones de Ocotlan", "rfc": null, "commercial_name": "Electroconstrucciones de Ocotlan"}	\N	102	2026-07-07 13:28:01.844417-06	2026-07-07 13:28:01.844417-06
\N	client.created	clients	105	null	{"legal_name": "EtCurae", "rfc": null, "commercial_name": "EtCurae"}	\N	106	2026-07-07 13:28:01.85393-06	2026-07-07 13:28:01.85393-06
\N	client.created	clients	109	null	{"legal_name": "FANOSA SA DE CV, Belen Almaraz", "rfc": null, "commercial_name": "FANOSA SA DE CV, Belen Almaraz"}	\N	110	2026-07-07 13:28:01.866175-06	2026-07-07 13:28:01.866175-06
\N	client.created	clients	113	null	{"legal_name": "FGR PROYECTOS INTEGRALES & INDUSTRIALES S.A DE C. V.", "rfc": null, "commercial_name": "FGR PROYECTOS INTEGRALES & INDUSTRIALES S.A DE C. V."}	\N	114	2026-07-07 13:28:01.87619-06	2026-07-07 13:28:01.87619-06
\N	client.created	clients	117	null	{"legal_name": "FLEXIBLES IMPRESOS Y LAMINADOS PARA LA INDUSTRIA", "rfc": null, "commercial_name": "FLEXIBLES IMPRESOS Y LAMINADOS PARA LA INDUSTRIA"}	\N	118	2026-07-07 13:28:01.886395-06	2026-07-07 13:28:01.886395-06
\N	client.created	clients	121	null	{"legal_name": "FRIMAX CARROCERIAS", "rfc": null, "commercial_name": "FRIMAX CARROCERIAS"}	\N	122	2026-07-07 13:28:01.89589-06	2026-07-07 13:28:01.89589-06
\N	client.created	clients	125	null	{"legal_name": "Farmacia del Carmen", "rfc": null, "commercial_name": "Farmacia del Carmen"}	\N	126	2026-07-07 13:28:01.906356-06	2026-07-07 13:28:01.906356-06
\N	client.created	clients	129	null	{"legal_name": "Food Microbiology Laboratories", "rfc": null, "commercial_name": "Food Microbiology Laboratories"}	\N	130	2026-07-07 13:28:01.915791-06	2026-07-07 13:28:01.915791-06
\N	client.created	clients	133	null	{"legal_name": "Francisco Javier Diaz Morales", "rfc": null, "commercial_name": "Francisco Javier Diaz Morales"}	\N	134	2026-07-07 13:28:01.926449-06	2026-07-07 13:28:01.926449-06
\N	client.created	clients	137	null	{"legal_name": "GPV Am\\u00e9ricas M\\u00e9xico, S.A.P.I. de C.V.", "rfc": null, "commercial_name": "GPV Am\\u00e9ricas M\\u00e9xico, S.A.P.I. de C.V."}	\N	138	2026-07-07 13:28:01.936817-06	2026-07-07 13:28:01.936817-06
\N	client.created	clients	141	null	{"legal_name": "Global Aceros", "rfc": null, "commercial_name": "Global Aceros"}	\N	142	2026-07-07 13:28:01.945328-06	2026-07-07 13:28:01.945328-06
\N	client.created	clients	145	null	{"legal_name": "Grupo Castaniel, S. de R.L. de C.V.", "rfc": null, "commercial_name": "Grupo Castaniel, S. de R.L. de C.V."}	\N	146	2026-07-07 13:28:01.953959-06	2026-07-07 13:28:01.953959-06
\N	client.created	clients	149	null	{"legal_name": "HARBISONWALKER INTERNATIONAL", "rfc": null, "commercial_name": "HARBISONWALKER INTERNATIONAL"}	\N	150	2026-07-07 13:28:01.962286-06	2026-07-07 13:28:01.962286-06
\N	client.created	clients	153	null	{"legal_name": "HONDA", "rfc": null, "commercial_name": "HONDA"}	\N	154	2026-07-07 13:28:01.970655-06	2026-07-07 13:28:01.970655-06
\N	client.created	clients	157	null	{"legal_name": "Hector Alejandro Ovalle Rendon, Other Address", "rfc": null, "commercial_name": "Hector Alejandro Ovalle Rendon, Other Address"}	\N	158	2026-07-07 13:28:01.979478-06	2026-07-07 13:28:01.979478-06
\N	client.created	clients	161	null	{"legal_name": "Hospital San Javier, S.A. de C.V.", "rfc": null, "commercial_name": "Hospital San Javier, S.A. de C.V."}	\N	162	2026-07-07 13:28:01.988585-06	2026-07-07 13:28:01.988585-06
\N	client.created	clients	165	null	{"legal_name": "IGNACIO GARCIA GARCIA", "rfc": null, "commercial_name": "IGNACIO GARCIA GARCIA"}	\N	166	2026-07-07 13:28:01.996972-06	2026-07-07 13:28:01.996972-06
\N	client.created	clients	169	null	{"legal_name": "INDICO GRASO", "rfc": null, "commercial_name": "INDICO GRASO"}	\N	170	2026-07-07 13:28:02.005604-06	2026-07-07 13:28:02.005604-06
\N	client.created	clients	173	null	{"legal_name": "INGENIERIA ESPECIALIZADA EN EFICIENCIA ENERGETICA", "rfc": null, "commercial_name": "INGENIERIA ESPECIALIZADA EN EFICIENCIA ENERGETICA"}	\N	174	2026-07-07 13:28:02.013415-06	2026-07-07 13:28:02.013415-06
\N	client.created	clients	177	null	{"legal_name": "INVENTRONICS", "rfc": null, "commercial_name": "INVENTRONICS"}	\N	178	2026-07-07 13:28:02.022546-06	2026-07-07 13:28:02.022546-06
\N	client.created	clients	181	null	{"legal_name": "Infraestructura e Ingenieria 360", "rfc": null, "commercial_name": "Infraestructura e Ingenieria 360"}	\N	182	2026-07-07 13:28:02.02963-06	2026-07-07 13:28:02.02963-06
\N	client.created	clients	185	null	{"legal_name": "Instrumentos Industriales del Pac\\u00edfico, S.A. de C.V.", "rfc": null, "commercial_name": "Instrumentos Industriales del Pac\\u00edfico, S.A. de C.V."}	\N	186	2026-07-07 13:28:02.03858-06	2026-07-07 13:28:02.03858-06
\N	client.created	clients	189	null	{"legal_name": "JOSE MANUEL AYALA DEL REAL", "rfc": null, "commercial_name": "JOSE MANUEL AYALA DEL REAL"}	\N	190	2026-07-07 13:28:02.047766-06	2026-07-07 13:28:02.047766-06
\N	client.created	clients	193	null	{"legal_name": "Jose Antonio Brise\\u00f1o Ortega", "rfc": null, "commercial_name": "Jose Antonio Brise\\u00f1o Ortega"}	\N	194	2026-07-07 13:28:02.055838-06	2026-07-07 13:28:02.055838-06
\N	client.deactivated	clients	72	{"is_active": true}	{"is_active": false}	\N	434	2026-07-07 16:36:36.426919-06	2026-07-07 16:36:36.426919-06
\N	client.created	clients	197	null	{"legal_name": "Kalex Transportes", "rfc": null, "commercial_name": "Kalex Transportes"}	\N	198	2026-07-07 13:28:02.062904-06	2026-07-07 13:28:02.062904-06
\N	client.created	clients	201	null	{"legal_name": "LCP PINTURAS Y SERVICIOS INDUSTRIALES", "rfc": null, "commercial_name": "LCP PINTURAS Y SERVICIOS INDUSTRIALES"}	\N	202	2026-07-07 13:28:02.070894-06	2026-07-07 13:28:02.070894-06
\N	client.created	clients	205	null	{"legal_name": "LSD DIAGNOSTICO DE ANALISIS CLINICOS", "rfc": null, "commercial_name": "LSD DIAGNOSTICO DE ANALISIS CLINICOS"}	\N	206	2026-07-07 13:28:02.078774-06	2026-07-07 13:28:02.078774-06
\N	client.created	clients	209	null	{"legal_name": "Lab Cor", "rfc": null, "commercial_name": "Lab Cor"}	\N	210	2026-07-07 13:28:02.086115-06	2026-07-07 13:28:02.086115-06
\N	client.created	clients	213	null	{"legal_name": "Laminados Extruidos Pl\\u00e1sticos, S.A. de C.V.", "rfc": null, "commercial_name": "Laminados Extruidos Pl\\u00e1sticos, S.A. de C.V."}	\N	214	2026-07-07 13:28:02.09485-06	2026-07-07 13:28:02.09485-06
\N	client.created	clients	217	null	{"legal_name": "MANUEL MORA", "rfc": null, "commercial_name": "MANUEL MORA"}	\N	218	2026-07-07 13:28:02.101554-06	2026-07-07 13:28:02.101554-06
\N	client.created	clients	221	null	{"legal_name": "MILENIO MOTORS", "rfc": null, "commercial_name": "MILENIO MOTORS"}	\N	222	2026-07-07 13:28:02.10938-06	2026-07-07 13:28:02.10938-06
\N	client.created	clients	225	null	{"legal_name": "MUNSA MOLINOS", "rfc": null, "commercial_name": "MUNSA MOLINOS"}	\N	226	2026-07-07 13:28:02.116919-06	2026-07-07 13:28:02.116919-06
\N	client.created	clients	229	null	{"legal_name": "Margrey Oficial", "rfc": null, "commercial_name": "Margrey Oficial"}	\N	230	2026-07-07 13:28:02.125937-06	2026-07-07 13:28:02.125937-06
\N	client.created	clients	233	null	{"legal_name": "Medikal Muneris", "rfc": null, "commercial_name": "Medikal Muneris"}	\N	234	2026-07-07 13:28:02.133598-06	2026-07-07 13:28:02.133598-06
\N	client.created	clients	237	null	{"legal_name": "Micropomex, S.A. de C.V.", "rfc": null, "commercial_name": "Micropomex, S.A. de C.V."}	\N	238	2026-07-07 13:28:02.14305-06	2026-07-07 13:28:02.14305-06
\N	client.created	clients	241	null	{"legal_name": "Mira de Occidente S.A. de C.V.", "rfc": null, "commercial_name": "Mira de Occidente S.A. de C.V."}	\N	242	2026-07-07 13:28:02.151445-06	2026-07-07 13:28:02.151445-06
\N	client.created	clients	245	null	{"legal_name": "NAOSA COUNTRY", "rfc": null, "commercial_name": "NAOSA COUNTRY"}	\N	246	2026-07-07 13:28:02.159907-06	2026-07-07 13:28:02.159907-06
\N	client.created	clients	249	null	{"legal_name": "NIRMAP", "rfc": null, "commercial_name": "NIRMAP"}	\N	250	2026-07-07 13:28:02.169287-06	2026-07-07 13:28:02.169287-06
\N	client.created	clients	253	null	{"legal_name": "Naturesweet plaza zapotlan", "rfc": null, "commercial_name": "Naturesweet plaza zapotlan"}	\N	254	2026-07-07 13:28:02.178327-06	2026-07-07 13:28:02.178327-06
\N	client.created	clients	257	null	{"legal_name": "OSA CONTROL DE CALIDAD", "rfc": null, "commercial_name": "OSA CONTROL DE CALIDAD"}	\N	258	2026-07-07 13:28:02.187154-06	2026-07-07 13:28:02.187154-06
\N	client.created	clients	261	null	{"legal_name": "Operadora Unidad de Investigacion en Salud de Chihuahua", "rfc": null, "commercial_name": "Operadora Unidad de Investigacion en Salud de Chihuahua"}	\N	262	2026-07-07 13:28:02.195451-06	2026-07-07 13:28:02.195451-06
\N	client.created	clients	265	null	{"legal_name": "POSTES Y PRECOLADOS INDUSTRIALES", "rfc": null, "commercial_name": "POSTES Y PRECOLADOS INDUSTRIALES"}	\N	266	2026-07-07 13:28:02.203349-06	2026-07-07 13:28:02.203349-06
\N	client.created	clients	269	null	{"legal_name": "PROYECTOS Y VALIDACIONES SORIMTEC", "rfc": null, "commercial_name": "PROYECTOS Y VALIDACIONES SORIMTEC"}	\N	270	2026-07-07 13:28:02.210993-06	2026-07-07 13:28:02.210993-06
\N	client.created	clients	273	null	{"legal_name": "Pigore Ingenieria", "rfc": null, "commercial_name": "Pigore Ingenieria"}	\N	274	2026-07-07 13:28:02.218478-06	2026-07-07 13:28:02.218478-06
\N	client.created	clients	277	null	{"legal_name": "P\\u00fablico", "rfc": null, "commercial_name": "P\\u00fablico"}	\N	278	2026-07-07 13:28:02.226377-06	2026-07-07 13:28:02.226377-06
\N	client.created	clients	281	null	{"legal_name": "ROSA MARIA MURILLO MACIAS", "rfc": null, "commercial_name": "ROSA MARIA MURILLO MACIAS"}	\N	282	2026-07-07 13:28:02.23349-06	2026-07-07 13:28:02.23349-06
\N	client.created	clients	285	null	{"legal_name": "Rinoinovation, S.A. de C.V.", "rfc": null, "commercial_name": "Rinoinovation, S.A. de C.V."}	\N	286	2026-07-07 13:28:02.241794-06	2026-07-07 13:28:02.241794-06
\N	client.created	clients	289	null	{"legal_name": "SAM MOTORS DE TORREON", "rfc": null, "commercial_name": "SAM MOTORS DE TORREON"}	\N	290	2026-07-07 13:28:02.248553-06	2026-07-07 13:28:02.248553-06
\N	client.created	clients	293	null	{"legal_name": "SANMINA", "rfc": null, "commercial_name": "SANMINA"}	\N	294	2026-07-07 13:28:02.256222-06	2026-07-07 13:28:02.256222-06
\N	client.created	clients	297	null	{"legal_name": "SERVIEMPAQUES 3G", "rfc": null, "commercial_name": "SERVIEMPAQUES 3G"}	\N	298	2026-07-07 13:28:02.26339-06	2026-07-07 13:28:02.26339-06
\N	client.created	clients	301	null	{"legal_name": "SOLAR PANEL COMPANY", "rfc": null, "commercial_name": "SOLAR PANEL COMPANY"}	\N	302	2026-07-07 13:28:02.271868-06	2026-07-07 13:28:02.271868-06
\N	client.created	clients	305	null	{"legal_name": "SS AUTOMAT", "rfc": null, "commercial_name": "SS AUTOMAT"}	\N	306	2026-07-07 13:28:02.314845-06	2026-07-07 13:28:02.314845-06
\N	client.created	clients	309	null	{"legal_name": "Sandvik Mining and Construction de M\\u00e9xico, S.A. de C.V.", "rfc": null, "commercial_name": "Sandvik Mining and Construction de M\\u00e9xico, S.A. de C.V."}	\N	310	2026-07-07 13:28:02.324365-06	2026-07-07 13:28:02.324365-06
\N	client.created	clients	313	null	{"legal_name": "Sanwa Screen Mexico, S.A. de C.V.", "rfc": null, "commercial_name": "Sanwa Screen Mexico, S.A. de C.V."}	\N	314	2026-07-07 13:28:02.332175-06	2026-07-07 13:28:02.332175-06
\N	client.created	clients	317	null	{"legal_name": "Semillas y Cereales San Juanico", "rfc": null, "commercial_name": "Semillas y Cereales San Juanico"}	\N	318	2026-07-07 13:28:02.342015-06	2026-07-07 13:28:02.342015-06
\N	client.created	clients	321	null	{"legal_name": "Shanaturals", "rfc": null, "commercial_name": "Shanaturals"}	\N	322	2026-07-07 13:28:02.350755-06	2026-07-07 13:28:02.350755-06
\N	client.created	clients	325	null	{"legal_name": "Sistema de Tren El\\u00e9ctrico Urbano", "rfc": null, "commercial_name": "Sistema de Tren El\\u00e9ctrico Urbano"}	\N	326	2026-07-07 13:28:02.359011-06	2026-07-07 13:28:02.359011-06
\N	client.created	clients	329	null	{"legal_name": "S\\u00e1nchez y Mart\\u00edn, S.A. de C.V.", "rfc": null, "commercial_name": "S\\u00e1nchez y Mart\\u00edn, S.A. de C.V."}	\N	330	2026-07-07 13:28:02.366012-06	2026-07-07 13:28:02.366012-06
\N	client.created	clients	333	null	{"legal_name": "TECNOLOGIAS COMINTEC, Lorena Flores", "rfc": null, "commercial_name": "TECNOLOGIAS COMINTEC, Lorena Flores"}	\N	334	2026-07-07 13:28:02.374626-06	2026-07-07 13:28:02.374626-06
\N	client.created	clients	337	null	{"legal_name": "Technology & Steel, S.A. de C.V.", "rfc": null, "commercial_name": "Technology & Steel, S.A. de C.V."}	\N	338	2026-07-07 13:28:02.383494-06	2026-07-07 13:28:02.383494-06
\N	client.created	clients	341	null	{"legal_name": "Trescal Calibraci\\u00f3n M\\u00e9xico S.A. de C.V.", "rfc": null, "commercial_name": "Trescal Calibraci\\u00f3n M\\u00e9xico S.A. de C.V."}	\N	342	2026-07-07 13:28:02.392547-06	2026-07-07 13:28:02.392547-06
\N	client.created	clients	345	null	{"legal_name": "Universal Wipes", "rfc": null, "commercial_name": "Universal Wipes"}	\N	346	2026-07-07 13:28:02.400014-06	2026-07-07 13:28:02.400014-06
\N	client.created	clients	349	null	{"legal_name": "Voit Automotive de M\\u00e9xico", "rfc": null, "commercial_name": "Voit Automotive de M\\u00e9xico"}	\N	350	2026-07-07 13:28:02.408026-06	2026-07-07 13:28:02.408026-06
\N	client.created	clients	353	null	{"legal_name": "WONDER FOODS MEXICO", "rfc": null, "commercial_name": "WONDER FOODS MEXICO"}	\N	354	2026-07-07 13:28:02.415312-06	2026-07-07 13:28:02.415312-06
\N	client.created	clients	357	null	{"legal_name": "YUTOTECH", "rfc": null, "commercial_name": "YUTOTECH"}	\N	358	2026-07-07 13:28:02.423409-06	2026-07-07 13:28:02.423409-06
\N	client.created	clients	199	null	{"legal_name": "Pascual Enrique Ojeda Herrera", "rfc": null, "commercial_name": "Pascual Enrique Ojeda Herrera"}	\N	200	2026-07-07 13:28:02.066924-06	2026-07-07 13:28:02.066924-06
\N	client.created	clients	203	null	{"legal_name": "LIZEN PATRIA", "rfc": null, "commercial_name": "LIZEN PATRIA"}	\N	204	2026-07-07 13:28:02.075391-06	2026-07-07 13:28:02.075391-06
\N	client.created	clients	207	null	{"legal_name": "LUIS ANGEL MEDINA VILLAGRAN", "rfc": null, "commercial_name": "LUIS ANGEL MEDINA VILLAGRAN"}	\N	208	2026-07-07 13:28:02.082207-06	2026-07-07 13:28:02.082207-06
\N	client.created	clients	211	null	{"legal_name": "Laboratorios Dibar", "rfc": null, "commercial_name": "Laboratorios Dibar"}	\N	212	2026-07-07 13:28:02.090951-06	2026-07-07 13:28:02.090951-06
\N	client.created	clients	215	null	{"legal_name": "Lizen Autos, S.A. de C.V", "rfc": null, "commercial_name": "Lizen Autos, S.A. de C.V"}	\N	216	2026-07-07 13:28:02.098213-06	2026-07-07 13:28:02.098213-06
\N	client.created	clients	219	null	{"legal_name": "METROLOGIA Y SERVICIOS MYC", "rfc": null, "commercial_name": "METROLOGIA Y SERVICIOS MYC"}	\N	220	2026-07-07 13:28:02.105722-06	2026-07-07 13:28:02.105722-06
\N	client.created	clients	223	null	{"legal_name": "MOTA ENGIL M\\u00c9XICO, S.A.P.I. DE C.V.", "rfc": null, "commercial_name": "MOTA ENGIL M\\u00c9XICO, S.A.P.I. DE C.V."}	\N	224	2026-07-07 13:28:02.113463-06	2026-07-07 13:28:02.113463-06
\N	client.created	clients	227	null	{"legal_name": "Madrigal Navarro, Francisco Sa\\u00fal", "rfc": null, "commercial_name": "Madrigal Navarro, Francisco Sa\\u00fal"}	\N	228	2026-07-07 13:28:02.121653-06	2026-07-07 13:28:02.121653-06
\N	client.created	clients	231	null	{"legal_name": "Mecanoplastica Industrial S. de R.L. de C.V.", "rfc": null, "commercial_name": "Mecanoplastica Industrial S. de R.L. de C.V."}	\N	232	2026-07-07 13:28:02.129262-06	2026-07-07 13:28:02.129262-06
\N	client.created	clients	235	null	{"legal_name": "Megaventilaci\\u00f3n, S.A. de C.V.", "rfc": null, "commercial_name": "Megaventilaci\\u00f3n, S.A. de C.V."}	\N	236	2026-07-07 13:28:02.138304-06	2026-07-07 13:28:02.138304-06
\N	client.created	clients	239	null	{"legal_name": "Miguel F", "rfc": null, "commercial_name": "Miguel F"}	\N	240	2026-07-07 13:28:02.147187-06	2026-07-07 13:28:02.147187-06
\N	client.created	clients	243	null	{"legal_name": "Moti prints", "rfc": null, "commercial_name": "Moti prints"}	\N	244	2026-07-07 13:28:02.155907-06	2026-07-07 13:28:02.155907-06
\N	client.created	clients	247	null	{"legal_name": "NB Foods", "rfc": null, "commercial_name": "NB Foods"}	\N	248	2026-07-07 13:28:02.165216-06	2026-07-07 13:28:02.165216-06
\N	client.created	clients	251	null	{"legal_name": "Naosa Volkswagen los Arcos", "rfc": null, "commercial_name": "Naosa Volkswagen los Arcos"}	\N	252	2026-07-07 13:28:02.173165-06	2026-07-07 13:28:02.173165-06
\N	client.created	clients	255	null	{"legal_name": "OPERADORA QU\\u00cdMICA MENLUN S.A.  DE C.V.", "rfc": null, "commercial_name": "OPERADORA QU\\u00cdMICA MENLUN S.A.  DE C.V."}	\N	256	2026-07-07 13:28:02.182764-06	2026-07-07 13:28:02.182764-06
\N	client.created	clients	259	null	{"legal_name": "Omnibus de M\\u00e9xico", "rfc": null, "commercial_name": "Omnibus de M\\u00e9xico"}	\N	260	2026-07-07 13:28:02.191546-06	2026-07-07 13:28:02.191546-06
\N	client.created	clients	263	null	{"legal_name": "P&A Integrity Management Company, S.A. de C.V.", "rfc": null, "commercial_name": "P&A Integrity Management Company, S.A. de C.V."}	\N	264	2026-07-07 13:28:02.199214-06	2026-07-07 13:28:02.199214-06
\N	client.created	clients	267	null	{"legal_name": "PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Alejandra Mart\\u00ednezi Cisneros", "rfc": null, "commercial_name": "PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Alejandra Mart\\u00ednezi Cisneros"}	\N	268	2026-07-07 13:28:02.20747-06	2026-07-07 13:28:02.20747-06
\N	client.created	clients	271	null	{"legal_name": "Panakos Plasma Marino, S.A. de C.V.", "rfc": null, "commercial_name": "Panakos Plasma Marino, S.A. de C.V."}	\N	272	2026-07-07 13:28:02.215014-06	2026-07-07 13:28:02.215014-06
\N	client.created	clients	275	null	{"legal_name": "Proveedora Comercial Alte\\u00f1a, S.A. de C.V.", "rfc": null, "commercial_name": "Proveedora Comercial Alte\\u00f1a, S.A. de C.V."}	\N	276	2026-07-07 13:28:02.222785-06	2026-07-07 13:28:02.222785-06
\N	client.created	clients	279	null	{"legal_name": "REYPCO REFRIGERACION Y PARTES PARA COMPRESORES SA DE CV", "rfc": null, "commercial_name": "REYPCO REFRIGERACION Y PARTES PARA COMPRESORES SA DE CV"}	\N	280	2026-07-07 13:28:02.229585-06	2026-07-07 13:28:02.229585-06
\N	client.created	clients	283	null	{"legal_name": "Raul Morales Orta", "rfc": null, "commercial_name": "Raul Morales Orta"}	\N	284	2026-07-07 13:28:02.237656-06	2026-07-07 13:28:02.237656-06
\N	client.created	clients	287	null	{"legal_name": "Rota Impresos Nueva Galicia, S.A. de C.V.", "rfc": null, "commercial_name": "Rota Impresos Nueva Galicia, S.A. de C.V."}	\N	288	2026-07-07 13:28:02.245484-06	2026-07-07 13:28:02.245484-06
\N	client.created	clients	291	null	{"legal_name": "SAMFRUT", "rfc": null, "commercial_name": "SAMFRUT"}	\N	292	2026-07-07 13:28:02.252102-06	2026-07-07 13:28:02.252102-06
\N	client.created	clients	295	null	{"legal_name": "SAVERGLASS", "rfc": null, "commercial_name": "SAVERGLASS"}	\N	296	2026-07-07 13:28:02.259786-06	2026-07-07 13:28:02.259786-06
\N	client.created	clients	299	null	{"legal_name": "SINCOF INGENIERIA", "rfc": null, "commercial_name": "SINCOF INGENIERIA"}	\N	300	2026-07-07 13:28:02.267502-06	2026-07-07 13:28:02.267502-06
\N	client.created	clients	303	null	{"legal_name": "SOLUCIONES POR ENCIMA DE TODO", "rfc": null, "commercial_name": "SOLUCIONES POR ENCIMA DE TODO"}	\N	304	2026-07-07 13:28:02.27567-06	2026-07-07 13:28:02.27567-06
\N	client.created	clients	307	null	{"legal_name": "SURMAN POLANCO", "rfc": null, "commercial_name": "SURMAN POLANCO"}	\N	308	2026-07-07 13:28:02.319501-06	2026-07-07 13:28:02.319501-06
\N	client.created	clients	311	null	{"legal_name": "Sane Foods", "rfc": null, "commercial_name": "Sane Foods"}	\N	312	2026-07-07 13:28:02.328276-06	2026-07-07 13:28:02.328276-06
\N	client.created	clients	315	null	{"legal_name": "Schenker International, S.A. de C.V.", "rfc": null, "commercial_name": "Schenker International, S.A. de C.V."}	\N	316	2026-07-07 13:28:02.337482-06	2026-07-07 13:28:02.337482-06
\N	client.created	clients	319	null	{"legal_name": "Servicios Profesionales Sor, S.A. de C.V.", "rfc": null, "commercial_name": "Servicios Profesionales Sor, S.A. de C.V."}	\N	320	2026-07-07 13:28:02.346208-06	2026-07-07 13:28:02.346208-06
\N	client.created	clients	323	null	{"legal_name": "Sialico", "rfc": null, "commercial_name": "Sialico"}	\N	324	2026-07-07 13:28:02.355233-06	2026-07-07 13:28:02.355233-06
\N	client.created	clients	327	null	{"legal_name": "Structures & industrial Services", "rfc": null, "commercial_name": "Structures & industrial Services"}	\N	328	2026-07-07 13:28:02.36267-06	2026-07-07 13:28:02.36267-06
\N	client.created	clients	331	null	{"legal_name": "TECNOCONTROL JALISCO", "rfc": null, "commercial_name": "TECNOCONTROL JALISCO"}	\N	332	2026-07-07 13:28:02.370416-06	2026-07-07 13:28:02.370416-06
\N	client.created	clients	335	null	{"legal_name": "TOTAL FARMA MEXICO", "rfc": null, "commercial_name": "TOTAL FARMA MEXICO"}	\N	336	2026-07-07 13:28:02.379262-06	2026-07-07 13:28:02.379262-06
\N	client.created	clients	339	null	{"legal_name": "Tecnoglobal PH7, S.A. de C.V.", "rfc": null, "commercial_name": "Tecnoglobal PH7, S.A. de C.V."}	\N	340	2026-07-07 13:28:02.388468-06	2026-07-07 13:28:02.388468-06
\N	client.created	clients	343	null	{"legal_name": "Tuercas y Abrazaderas Ensa, S.A. de C.V.", "rfc": null, "commercial_name": "Tuercas y Abrazaderas Ensa, S.A. de C.V."}	\N	344	2026-07-07 13:28:02.396257-06	2026-07-07 13:28:02.396257-06
\N	client.created	clients	347	null	{"legal_name": "Vamsa las Fuentes", "rfc": null, "commercial_name": "Vamsa las Fuentes"}	\N	348	2026-07-07 13:28:02.404111-06	2026-07-07 13:28:02.404111-06
\N	client.created	clients	351	null	{"legal_name": "Volkswagen del Centro", "rfc": null, "commercial_name": "Volkswagen del Centro"}	\N	352	2026-07-07 13:28:02.41176-06	2026-07-07 13:28:02.41176-06
\N	client.created	clients	355	null	{"legal_name": "Wolfsburg de Occidente", "rfc": null, "commercial_name": "Wolfsburg de Occidente"}	\N	356	2026-07-07 13:28:02.418794-06	2026-07-07 13:28:02.418794-06
\N	client.created	clients	206	null	{"legal_name": "LSD DIAGNOSTICO DE ANALISIS CLINICOS, Luis Angel Rostro", "rfc": null, "commercial_name": "LSD DIAGNOSTICO DE ANALISIS CLINICOS, Luis Angel Rostro"}	\N	207	2026-07-07 13:28:02.080423-06	2026-07-07 13:28:02.080423-06
\N	client.created	clients	210	null	{"legal_name": "Laboratorio Santo Domingo", "rfc": null, "commercial_name": "Laboratorio Santo Domingo"}	\N	211	2026-07-07 13:28:02.088568-06	2026-07-07 13:28:02.088568-06
\N	client.created	clients	214	null	{"legal_name": "Lic. Georgette Hamden Mu\\u00f1oz", "rfc": null, "commercial_name": "Lic. Georgette Hamden Mu\\u00f1oz"}	\N	215	2026-07-07 13:28:02.096536-06	2026-07-07 13:28:02.096536-06
\N	client.created	clients	218	null	{"legal_name": "MC Procesos en Papel y Cart\\u00f3n", "rfc": null, "commercial_name": "MC Procesos en Papel y Cart\\u00f3n"}	\N	219	2026-07-07 13:28:02.10341-06	2026-07-07 13:28:02.10341-06
\N	client.created	clients	222	null	{"legal_name": "MOLEX DE MEXICO GUADALAJARA 2, S DE RL DE CV", "rfc": null, "commercial_name": "MOLEX DE MEXICO GUADALAJARA 2, S DE RL DE CV"}	\N	223	2026-07-07 13:28:02.110965-06	2026-07-07 13:28:02.110965-06
\N	client.created	clients	226	null	{"legal_name": "Madison Constructores", "rfc": null, "commercial_name": "Madison Constructores"}	\N	227	2026-07-07 13:28:02.119028-06	2026-07-07 13:28:02.119028-06
\N	client.created	clients	230	null	{"legal_name": "Mayoreo Ferretero Atlas", "rfc": null, "commercial_name": "Mayoreo Ferretero Atlas"}	\N	231	2026-07-07 13:28:02.127613-06	2026-07-07 13:28:02.127613-06
\N	client.created	clients	234	null	{"legal_name": "Medilab Diagnostico Medico Empresarial S. de R.L. de C.V.", "rfc": null, "commercial_name": "Medilab Diagnostico Medico Empresarial S. de R.L. de C.V."}	\N	235	2026-07-07 13:28:02.136199-06	2026-07-07 13:28:02.136199-06
\N	client.created	clients	238	null	{"legal_name": "Migu", "rfc": null, "commercial_name": "Migu"}	\N	239	2026-07-07 13:28:02.145016-06	2026-07-07 13:28:02.145016-06
\N	client.created	clients	242	null	{"legal_name": "Mitza Facturaci\\u00f3n", "rfc": null, "commercial_name": "Mitza Facturaci\\u00f3n"}	\N	243	2026-07-07 13:28:02.153875-06	2026-07-07 13:28:02.153875-06
\N	client.created	clients	246	null	{"legal_name": "NATURAL SYRUP PRODUCER", "rfc": null, "commercial_name": "NATURAL SYRUP PRODUCER"}	\N	247	2026-07-07 13:28:02.163001-06	2026-07-07 13:28:02.163001-06
\N	client.created	clients	250	null	{"legal_name": "NUKUL Grupo Comercializador", "rfc": null, "commercial_name": "NUKUL Grupo Comercializador"}	\N	251	2026-07-07 13:28:02.1712-06	2026-07-07 13:28:02.1712-06
\N	client.created	clients	254	null	{"legal_name": "OLGA LIDIA CORTES VILLAGRAN", "rfc": null, "commercial_name": "OLGA LIDIA CORTES VILLAGRAN"}	\N	255	2026-07-07 13:28:02.180537-06	2026-07-07 13:28:02.180537-06
\N	client.created	clients	258	null	{"legal_name": "Omar Alejandro Aceves Camacho", "rfc": null, "commercial_name": "Omar Alejandro Aceves Camacho"}	\N	259	2026-07-07 13:28:02.189264-06	2026-07-07 13:28:02.189264-06
\N	client.created	clients	262	null	{"legal_name": "Ortopedi Salud", "rfc": null, "commercial_name": "Ortopedi Salud"}	\N	263	2026-07-07 13:28:02.197102-06	2026-07-07 13:28:02.197102-06
\N	client.created	clients	266	null	{"legal_name": "PROEMPAQUE", "rfc": null, "commercial_name": "PROEMPAQUE"}	\N	267	2026-07-07 13:28:02.205461-06	2026-07-07 13:28:02.205461-06
\N	client.created	clients	270	null	{"legal_name": "Pack System, S.A. de C.V.", "rfc": null, "commercial_name": "Pack System, S.A. de C.V."}	\N	271	2026-07-07 13:28:02.213417-06	2026-07-07 13:28:02.213417-06
\N	client.created	clients	274	null	{"legal_name": "Pont Aurell y Armengol MEXICO SA de CV", "rfc": null, "commercial_name": "Pont Aurell y Armengol MEXICO SA de CV"}	\N	275	2026-07-07 13:28:02.220597-06	2026-07-07 13:28:02.220597-06
\N	client.created	clients	278	null	{"legal_name": "P\\u00fablico general", "rfc": null, "commercial_name": "P\\u00fablico general"}	\N	279	2026-07-07 13:28:02.228031-06	2026-07-07 13:28:02.228031-06
\N	client.created	clients	282	null	{"legal_name": "RY Candy, S.A. de C.V.", "rfc": null, "commercial_name": "RY Candy, S.A. de C.V."}	\N	283	2026-07-07 13:28:02.235309-06	2026-07-07 13:28:02.235309-06
\N	client.created	clients	286	null	{"legal_name": "Rogers Foam", "rfc": null, "commercial_name": "Rogers Foam"}	\N	287	2026-07-07 13:28:02.243478-06	2026-07-07 13:28:02.243478-06
\N	client.created	clients	290	null	{"legal_name": "SAMADHI LUCIA CARDENAS LIMON", "rfc": null, "commercial_name": "SAMADHI LUCIA CARDENAS LIMON"}	\N	291	2026-07-07 13:28:02.250308-06	2026-07-07 13:28:02.250308-06
\N	client.created	clients	294	null	{"legal_name": "SAUL ISAAC ARCE CORTES", "rfc": null, "commercial_name": "SAUL ISAAC ARCE CORTES"}	\N	295	2026-07-07 13:28:02.258157-06	2026-07-07 13:28:02.258157-06
\N	client.created	clients	298	null	{"legal_name": "SIALICO FOOD SAFETY", "rfc": null, "commercial_name": "SIALICO FOOD SAFETY"}	\N	299	2026-07-07 13:28:02.265363-06	2026-07-07 13:28:02.265363-06
\N	client.created	clients	302	null	{"legal_name": "SOLUCIONES INTELIGENTES SIHRO", "rfc": null, "commercial_name": "SOLUCIONES INTELIGENTES SIHRO"}	\N	303	2026-07-07 13:28:02.273915-06	2026-07-07 13:28:02.273915-06
\N	client.created	clients	306	null	{"legal_name": "STEEL MASTER STRUCTURES MX", "rfc": null, "commercial_name": "STEEL MASTER STRUCTURES MX"}	\N	307	2026-07-07 13:28:02.317222-06	2026-07-07 13:28:02.317222-06
\N	client.created	clients	310	null	{"legal_name": "Sandvik Mining and Construction de M\\u00e9xico, S.A. de C.V., Monica cisneros", "rfc": null, "commercial_name": "Sandvik Mining and Construction de M\\u00e9xico, S.A. de C.V., Monica cisneros"}	\N	311	2026-07-07 13:28:02.326543-06	2026-07-07 13:28:02.326543-06
\N	client.created	clients	314	null	{"legal_name": "Saz\\u00f3n Natural", "rfc": null, "commercial_name": "Saz\\u00f3n Natural"}	\N	315	2026-07-07 13:28:02.334618-06	2026-07-07 13:28:02.334618-06
\N	client.created	clients	318	null	{"legal_name": "Servicios Enga Ingenieria S.C.", "rfc": null, "commercial_name": "Servicios Enga Ingenieria S.C."}	\N	319	2026-07-07 13:28:02.344309-06	2026-07-07 13:28:02.344309-06
\N	client.created	clients	322	null	{"legal_name": "Sherex M\\u00e9xico", "rfc": null, "commercial_name": "Sherex M\\u00e9xico"}	\N	323	2026-07-07 13:28:02.352786-06	2026-07-07 13:28:02.352786-06
\N	client.created	clients	326	null	{"legal_name": "Sistemas Electricos Industriales y Comerciales", "rfc": null, "commercial_name": "Sistemas Electricos Industriales y Comerciales"}	\N	327	2026-07-07 13:28:02.360743-06	2026-07-07 13:28:02.360743-06
\N	client.created	clients	330	null	{"legal_name": "TECHNOLOGY & STEEL", "rfc": null, "commercial_name": "TECHNOLOGY & STEEL"}	\N	331	2026-07-07 13:28:02.368245-06	2026-07-07 13:28:02.368245-06
\N	client.created	clients	334	null	{"legal_name": "TOP HEALTH", "rfc": null, "commercial_name": "TOP HEALTH"}	\N	335	2026-07-07 13:28:02.376982-06	2026-07-07 13:28:02.376982-06
\N	client.created	clients	338	null	{"legal_name": "Tecnoglobal", "rfc": null, "commercial_name": "Tecnoglobal"}	\N	339	2026-07-07 13:28:02.386359-06	2026-07-07 13:28:02.386359-06
\N	client.created	clients	342	null	{"legal_name": "Tubos y Aceros Maquinados", "rfc": null, "commercial_name": "Tubos y Aceros Maquinados"}	\N	343	2026-07-07 13:28:02.394229-06	2026-07-07 13:28:02.394229-06
\N	client.created	clients	346	null	{"legal_name": "VAQCSA GUADALAJARA", "rfc": null, "commercial_name": "VAQCSA GUADALAJARA"}	\N	347	2026-07-07 13:28:02.402015-06	2026-07-07 13:28:02.402015-06
\N	client.created	clients	350	null	{"legal_name": "Volkswagen Galerias", "rfc": null, "commercial_name": "Volkswagen Galerias"}	\N	351	2026-07-07 13:28:02.410128-06	2026-07-07 13:28:02.410128-06
\N	client.created	clients	354	null	{"legal_name": "Wasion, S. de R.L. de C.V.", "rfc": null, "commercial_name": "Wasion, S. de R.L. de C.V."}	\N	355	2026-07-07 13:28:02.416929-06	2026-07-07 13:28:02.416929-06
\N	client.created	clients	358	null	{"legal_name": "ZF Suspensi\\u00f3n Technology Guadalajara, S.A. de C.V.", "rfc": null, "commercial_name": "ZF Suspensi\\u00f3n Technology Guadalajara, S.A. de C.V."}	\N	359	2026-07-07 13:28:02.425077-06	2026-07-07 13:28:02.425077-06
\N	client.created	clients	362	null	{"legal_name": "cem", "rfc": null, "commercial_name": "cem"}	\N	363	2026-07-07 13:28:02.433076-06	2026-07-07 13:28:02.433076-06
\N	client.deactivated	clients	73	{"is_active": true}	{"is_active": false}	\N	435	2026-07-07 16:36:36.445538-06	2026-07-07 16:36:36.445538-06
\N	client.created	clients	212	null	{"legal_name": "Laboratorios Zeyco", "rfc": null, "commercial_name": "Laboratorios Zeyco"}	\N	213	2026-07-07 13:28:02.092749-06	2026-07-07 13:28:02.092749-06
\N	client.created	clients	216	null	{"legal_name": "MANOMETROS DE JALISCO", "rfc": null, "commercial_name": "MANOMETROS DE JALISCO"}	\N	217	2026-07-07 13:28:02.099817-06	2026-07-07 13:28:02.099817-06
\N	client.created	clients	220	null	{"legal_name": "MIGUEL ANGEL MU\\u00d1OZ TORRES", "rfc": null, "commercial_name": "MIGUEL ANGEL MU\\u00d1OZ TORRES"}	\N	221	2026-07-07 13:28:02.107719-06	2026-07-07 13:28:02.107719-06
\N	client.created	clients	224	null	{"legal_name": "MTQ DE MEXICO", "rfc": null, "commercial_name": "MTQ DE MEXICO"}	\N	225	2026-07-07 13:28:02.115089-06	2026-07-07 13:28:02.115089-06
\N	client.created	clients	228	null	{"legal_name": "Mafain Integraci\\u00f3n Industrial, S.A. de C.V.", "rfc": null, "commercial_name": "Mafain Integraci\\u00f3n Industrial, S.A. de C.V."}	\N	229	2026-07-07 13:28:02.124229-06	2026-07-07 13:28:02.124229-06
\N	client.created	clients	232	null	{"legal_name": "Medetic Corp", "rfc": null, "commercial_name": "Medetic Corp"}	\N	233	2026-07-07 13:28:02.130902-06	2026-07-07 13:28:02.130902-06
\N	client.created	clients	236	null	{"legal_name": "Metrologia Zelkova", "rfc": null, "commercial_name": "Metrologia Zelkova"}	\N	237	2026-07-07 13:28:02.140683-06	2026-07-07 13:28:02.140683-06
\N	client.created	clients	240	null	{"legal_name": "Miguel Felipe Ordaz Higareda", "rfc": null, "commercial_name": "Miguel Felipe Ordaz Higareda"}	\N	241	2026-07-07 13:28:02.149273-06	2026-07-07 13:28:02.149273-06
\N	client.created	clients	244	null	{"legal_name": "Motidigital, nian zet rojas ramos", "rfc": null, "commercial_name": "Motidigital, nian zet rojas ramos"}	\N	245	2026-07-07 13:28:02.15792-06	2026-07-07 13:28:02.15792-06
\N	client.created	clients	248	null	{"legal_name": "NG EXTRUSION", "rfc": null, "commercial_name": "NG EXTRUSION"}	\N	249	2026-07-07 13:28:02.167291-06	2026-07-07 13:28:02.167291-06
\N	client.created	clients	252	null	{"legal_name": "Naturesweet Invernaderos, S. de R.L. de C.V.", "rfc": null, "commercial_name": "Naturesweet Invernaderos, S. de R.L. de C.V."}	\N	253	2026-07-07 13:28:02.175703-06	2026-07-07 13:28:02.175703-06
\N	client.created	clients	256	null	{"legal_name": "OPKO Pharmaceuticals", "rfc": null, "commercial_name": "OPKO Pharmaceuticals"}	\N	257	2026-07-07 13:28:02.185-06	2026-07-07 13:28:02.185-06
\N	client.created	clients	260	null	{"legal_name": "Operadora Chivas", "rfc": null, "commercial_name": "Operadora Chivas"}	\N	261	2026-07-07 13:28:02.193368-06	2026-07-07 13:28:02.193368-06
\N	client.created	clients	264	null	{"legal_name": "PAMO DE OCCIDENTE", "rfc": null, "commercial_name": "PAMO DE OCCIDENTE"}	\N	265	2026-07-07 13:28:02.201281-06	2026-07-07 13:28:02.201281-06
\N	client.created	clients	268	null	{"legal_name": "PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Omar  Chiquini Zamora", "rfc": null, "commercial_name": "PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Omar  Chiquini Zamora"}	\N	269	2026-07-07 13:28:02.209279-06	2026-07-07 13:28:02.209279-06
\N	client.created	clients	272	null	{"legal_name": "Peiyuan Automobile Parts Manufacture, S.A. de C.V.", "rfc": null, "commercial_name": "Peiyuan Automobile Parts Manufacture, S.A. de C.V."}	\N	273	2026-07-07 13:28:02.216638-06	2026-07-07 13:28:02.216638-06
\N	client.created	clients	276	null	{"legal_name": "Pym Proyectos y Montajes, S.A. de C.V .", "rfc": null, "commercial_name": "Pym Proyectos y Montajes, S.A. de C.V ."}	\N	277	2026-07-07 13:28:02.224768-06	2026-07-07 13:28:02.224768-06
\N	client.created	clients	280	null	{"legal_name": "RICARDO IVAN RAMIREZ GARCIA", "rfc": null, "commercial_name": "RICARDO IVAN RAMIREZ GARCIA"}	\N	281	2026-07-07 13:28:02.231825-06	2026-07-07 13:28:02.231825-06
\N	client.created	clients	284	null	{"legal_name": "Ricardo Javier Trillo Villalobos", "rfc": null, "commercial_name": "Ricardo Javier Trillo Villalobos"}	\N	285	2026-07-07 13:28:02.239909-06	2026-07-07 13:28:02.239909-06
\N	client.created	clients	288	null	{"legal_name": "Royal Gaskets & Joins", "rfc": null, "commercial_name": "Royal Gaskets & Joins"}	\N	289	2026-07-07 13:28:02.246994-06	2026-07-07 13:28:02.246994-06
\N	client.created	clients	292	null	{"legal_name": "SANDRA CECILIA PRECIADO CAMPILLO", "rfc": null, "commercial_name": "SANDRA CECILIA PRECIADO CAMPILLO"}	\N	293	2026-07-07 13:28:02.254209-06	2026-07-07 13:28:02.254209-06
\N	client.created	clients	296	null	{"legal_name": "SELMA DANIELA SANCHEZ ORTIZ", "rfc": null, "commercial_name": "SELMA DANIELA SANCHEZ ORTIZ"}	\N	297	2026-07-07 13:28:02.261704-06	2026-07-07 13:28:02.261704-06
\N	client.created	clients	300	null	{"legal_name": "SIS COMEDORES", "rfc": null, "commercial_name": "SIS COMEDORES"}	\N	301	2026-07-07 13:28:02.269772-06	2026-07-07 13:28:02.269772-06
\N	client.created	clients	304	null	{"legal_name": "SOPORTE ELECTRICO INTERNACIONAL", "rfc": null, "commercial_name": "SOPORTE ELECTRICO INTERNACIONAL"}	\N	305	2026-07-07 13:28:02.312592-06	2026-07-07 13:28:02.312592-06
\N	client.created	clients	308	null	{"legal_name": "Saleiko Industrial", "rfc": null, "commercial_name": "Saleiko Industrial"}	\N	309	2026-07-07 13:28:02.321773-06	2026-07-07 13:28:02.321773-06
\N	client.created	clients	312	null	{"legal_name": "Santiago Torres Flores", "rfc": null, "commercial_name": "Santiago Torres Flores"}	\N	313	2026-07-07 13:28:02.329954-06	2026-07-07 13:28:02.329954-06
\N	client.created	clients	316	null	{"legal_name": "Schott de M\\u00e9xico, S.A. de C.V.", "rfc": null, "commercial_name": "Schott de M\\u00e9xico, S.A. de C.V."}	\N	317	2026-07-07 13:28:02.339798-06	2026-07-07 13:28:02.339798-06
\N	client.created	clients	320	null	{"legal_name": "Servishell", "rfc": null, "commercial_name": "Servishell"}	\N	321	2026-07-07 13:28:02.348734-06	2026-07-07 13:28:02.348734-06
\N	client.created	clients	324	null	{"legal_name": "Sims Lifecycle Services", "rfc": null, "commercial_name": "Sims Lifecycle Services"}	\N	325	2026-07-07 13:28:02.357295-06	2026-07-07 13:28:02.357295-06
\N	client.created	clients	328	null	{"legal_name": "Suministros y Sanidad RX", "rfc": null, "commercial_name": "Suministros y Sanidad RX"}	\N	329	2026-07-07 13:28:02.364325-06	2026-07-07 13:28:02.364325-06
\N	client.created	clients	332	null	{"legal_name": "TECNOCONTROL JALISCO, TECNOCONTROL JALISCO", "rfc": null, "commercial_name": "TECNOCONTROL JALISCO, TECNOCONTROL JALISCO"}	\N	333	2026-07-07 13:28:02.372173-06	2026-07-07 13:28:02.372173-06
\N	client.created	clients	336	null	{"legal_name": "TRANS & LOG HSA", "rfc": null, "commercial_name": "TRANS & LOG HSA"}	\N	337	2026-07-07 13:28:02.381446-06	2026-07-07 13:28:02.381446-06
\N	client.created	clients	340	null	{"legal_name": "Telecontroles de Guadalajara", "rfc": null, "commercial_name": "Telecontroles de Guadalajara"}	\N	341	2026-07-07 13:28:02.390804-06	2026-07-07 13:28:02.390804-06
\N	client.created	clients	344	null	{"legal_name": "UNION GASTRONOMICA B Y S", "rfc": null, "commercial_name": "UNION GASTRONOMICA B Y S"}	\N	345	2026-07-07 13:28:02.398257-06	2026-07-07 13:28:02.398257-06
\N	client.created	clients	348	null	{"legal_name": "Vidara", "rfc": null, "commercial_name": "Vidara"}	\N	349	2026-07-07 13:28:02.406118-06	2026-07-07 13:28:02.406118-06
\N	client.created	clients	352	null	{"legal_name": "V\\u00e1lvulas y Asesor\\u00eda Integral en Termopl\\u00e1sticos, S.A. de C.V.", "rfc": null, "commercial_name": "V\\u00e1lvulas y Asesor\\u00eda Integral en Termopl\\u00e1sticos, S.A. de C.V."}	\N	353	2026-07-07 13:28:02.413652-06	2026-07-07 13:28:02.413652-06
\N	client.created	clients	356	null	{"legal_name": "YALIERCP", "rfc": null, "commercial_name": "YALIERCP"}	\N	357	2026-07-07 13:28:02.4211-06	2026-07-07 13:28:02.4211-06
\N	client.created	clients	360	null	{"legal_name": "Zar kruse", "rfc": null, "commercial_name": "Zar kruse"}	\N	361	2026-07-07 13:28:02.428947-06	2026-07-07 13:28:02.428947-06
\N	client.created	clients	364	null	{"legal_name": "generico", "rfc": null, "commercial_name": "generico"}	\N	365	2026-07-07 13:28:02.438009-06	2026-07-07 13:28:02.438009-06
\N	client.created	clients	368	null	{"legal_name": "laboratorios DICA", "rfc": null, "commercial_name": "laboratorios DICA"}	\N	369	2026-07-07 13:28:02.445091-06	2026-07-07 13:28:02.445091-06
\N	client.created	clients	372	null	{"legal_name": "volkswan galerias", "rfc": null, "commercial_name": "volkswan galerias"}	\N	373	2026-07-07 13:28:02.4523-06	2026-07-07 13:28:02.4523-06
\N	client.created	clients	359	null	{"legal_name": "ZURICH TEC DE MEXICO", "rfc": null, "commercial_name": "ZURICH TEC DE MEXICO"}	\N	360	2026-07-07 13:28:02.426648-06	2026-07-07 13:28:02.426648-06
\N	client.created	clients	363	null	{"legal_name": "diprocat", "rfc": null, "commercial_name": "diprocat"}	\N	364	2026-07-07 13:28:02.435347-06	2026-07-07 13:28:02.435347-06
\N	client.created	clients	367	null	{"legal_name": "joselyne.barron@uwipes.com", "rfc": null, "commercial_name": "joselyne.barron@uwipes.com"}	\N	368	2026-07-07 13:28:02.443524-06	2026-07-07 13:28:02.443524-06
\N	client.created	clients	371	null	{"legal_name": "sola", "rfc": null, "commercial_name": "sola"}	\N	372	2026-07-07 13:28:02.450563-06	2026-07-07 13:28:02.450563-06
\N	client.created	clients	361	null	{"legal_name": "asesores sire", "rfc": null, "commercial_name": "asesores sire"}	\N	362	2026-07-07 13:28:02.430881-06	2026-07-07 13:28:02.430881-06
\N	client.created	clients	365	null	{"legal_name": "gerentecalidad@margrey.com.mx", "rfc": null, "commercial_name": "gerentecalidad@margrey.com.mx"}	\N	366	2026-07-07 13:28:02.440127-06	2026-07-07 13:28:02.440127-06
\N	client.created	clients	369	null	{"legal_name": "mario.munoz@fgr.org.mx", "rfc": null, "commercial_name": "mario.munoz@fgr.org.mx"}	\N	370	2026-07-07 13:28:02.446634-06	2026-07-07 13:28:02.446634-06
\N	client.created	clients	370	null	{"legal_name": "scho", "rfc": null, "commercial_name": "scho"}	\N	371	2026-07-07 13:28:02.448519-06	2026-07-07 13:28:02.448519-06
1	user.created	users	2	null	{"email": "monse@myc.com", "full_name": "monse cortes", "is_active": true, "role_names": ["Administrador"]}	Usuario creado desde configuracion	374	2026-07-07 14:15:51.978436-06	2026-07-07 14:15:51.978436-06
1	user.deactivated	users	2	{"email": "monse@myc.com", "full_name": "monse cortes", "is_active": true, "role_names": ["Administrador"]}	{"email": "monse@myc.com", "full_name": "monse cortes", "is_active": false, "role_names": ["Administrador"]}	Cambio de estado de usuario	375	2026-07-07 14:27:55.164792-06	2026-07-07 14:27:55.164792-06
\N	client.updated	clients	1	{"client_type": "persona_moral", "legal_name": "A quien corresponda", "commercial_name": "A quien corresponda", "rfc": null, "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": null, "phone": null, "tax_regime": null, "cfdi_use": null, "street_type": null, "street": null, "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": null, "city": null, "state": null, "postal_code": null, "country": "Mexico", "fiscal_postal_code": null, "contacts": []}	{"client_type": "persona_moral", "legal_name": "METROLOGIA Y SERVICIOS MYC", "commercial_name": "METROLOGIA Y SERVICIOS MYC", "rfc": "MSM180712686", "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": null, "phone": null, "tax_regime": "R\\u00e9gimen General de Ley Personas Morales", "cfdi_use": null, "street_type": "CALLE", "street": "AV. CRISTOBAL COLON", "exterior_number": "6086", "interior_number": "57", "neighborhood": "VILLA DE SANTA MARIA", "locality": "TLAQUEPAQUE", "municipality": "SAN PEDRO TLAQUEPAQUE", "city": "SAN PEDRO TLAQUEPAQUE", "state": "JALISCO", "postal_code": "45601", "country": "Mexico", "fiscal_postal_code": "45601", "contacts": []}	\N	376	2026-07-07 14:33:36.66951-06	2026-07-07 14:33:36.66951-06
\N	client.tax_constancy_uploaded	clients	1	{"tax_constancy_filename": null, "tax_constancy_path": null}	{"tax_constancy_filename": "Csf_MSM180712686.pdf", "tax_constancy_path": "clientes/cliente_1/constancia_fiscal_5e0f2c597a334762a7786187765d3477.pdf"}	\N	377	2026-07-07 14:33:36.710314-06	2026-07-07 14:33:36.710314-06
\N	client.updated	clients	2	{"client_type": "persona_moral", "legal_name": "ABASTECEDORA DE INSUMOS PARA LA SALUD", "commercial_name": "ABASTECEDORA DE INSUMOS PARA LA SALUD", "rfc": null, "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "responsable.sanitario@abisalud.com", "phone": null, "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "NORTE 31 A, NUEVA INDUSTRIAL VALLEJO", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "GUSTAVO A MADERO", "city": "GUSTAVO A MADERO", "state": "Ciudad de M\\u00e9xico", "postal_code": "07700", "country": "Mexico", "fiscal_postal_code": "07700", "contacts": []}	{"client_type": "persona_moral", "legal_name": "ABASTECEDORA DE INSUMOS PARA LA SALUD", "commercial_name": "ABASTECEDORA DE INSUMOS PARA LA SALUD", "rfc": "XAXX010101000", "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "responsable.sanitario@abisalud.com", "phone": null, "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "NORTE 31 A, NUEVA INDUSTRIAL VALLEJO", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "GUSTAVO A MADERO", "city": "GUSTAVO A MADERO", "state": "Ciudad de M\\u00e9xico", "postal_code": "07700", "country": "Mexico", "fiscal_postal_code": "07700", "contacts": []}	\N	378	2026-07-07 14:36:12.983904-06	2026-07-07 14:36:12.983904-06
\N	client.updated	clients	21	{"client_type": "persona_moral", "legal_name": "Adler Pharma, S. de R.L. de C.V.", "commercial_name": "Adler Pharma, S. de R.L. de C.V.", "rfc": null, "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "luis.varela@adler-la.com", "phone": "+52 33 3033 7809", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "Miguel Alem\\u00e1n No. 6926", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "Zapopan", "city": "Zapopan", "state": "Jalisco", "postal_code": "45236", "country": "Mexico", "fiscal_postal_code": "45236", "contacts": [{"name": "Luis Varela", "email": "luis.varela@adler-la.com", "phone": "+52 33 3033 7809"}]}	{"client_type": "persona_moral", "legal_name": "Adler Pharma, S. de R.L. de C.V.", "commercial_name": "Adler Pharma, S. de R.L. de C.V.", "rfc": "XAXX010101000", "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "luis.varela@adler-la.com", "phone": "+52 33 3033 7809", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "Miguel Alem\\u00e1n No. 6926", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "Zapopan", "city": "Zapopan", "state": "Jalisco", "postal_code": "45236", "country": "Mexico", "fiscal_postal_code": "45236", "contacts": [{"name": "Luis Varela", "email": "luis.varela@adler-la.com", "phone": "+52 33 3033 7809", "position": null}]}	\N	379	2026-07-07 14:36:19.733733-06	2026-07-07 14:36:19.733733-06
\N	client.updated	clients	3	{"client_type": "persona_moral", "legal_name": "ADM Packaging Services S de RL de CV", "commercial_name": "ADM Packaging Services S de RL de CV", "rfc": null, "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "Miriam@admpackaging.com", "phone": "+52 353 123 8640", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "Puerto Ensenada 1075, Col. Miramar", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "Zapopan", "city": "Zapopan", "state": "Jalisco", "postal_code": null, "country": "Mexico", "fiscal_postal_code": null, "contacts": []}	{"client_type": "persona_moral", "legal_name": "ADM Packaging Services S de RL de CV", "commercial_name": "ADM Packaging Services S de RL de CV", "rfc": "XAXX010101000", "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "Miriam@admpackaging.com", "phone": "+52 353 123 8640", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "Puerto Ensenada 1075, Col. Miramar", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "Zapopan", "city": "Zapopan", "state": "Jalisco", "postal_code": null, "country": "Mexico", "fiscal_postal_code": null, "contacts": []}	\N	380	2026-07-07 14:36:25.916315-06	2026-07-07 14:36:25.916315-06
\N	client.deactivated	clients	74	{"is_active": true}	{"is_active": false}	\N	436	2026-07-07 16:36:36.459641-06	2026-07-07 16:36:36.459641-06
\N	client.deactivated	clients	362	{"is_active": true}	{"is_active": false}	\N	437	2026-07-07 16:36:36.471045-06	2026-07-07 16:36:36.471045-06
\N	client.deactivated	clients	46	{"is_active": true}	{"is_active": false}	\N	438	2026-07-07 16:36:36.480529-06	2026-07-07 16:36:36.480529-06
\N	client.deactivated	clients	47	{"is_active": true}	{"is_active": false}	\N	439	2026-07-07 16:36:36.490623-06	2026-07-07 16:36:36.490623-06
\N	client.deactivated	clients	75	{"is_active": true}	{"is_active": false}	\N	440	2026-07-07 16:36:36.502298-06	2026-07-07 16:36:36.502298-06
\N	client.deactivated	clients	48	{"is_active": true}	{"is_active": false}	\N	441	2026-07-07 16:36:36.511675-06	2026-07-07 16:36:36.511675-06
\N	client.deactivated	clients	49	{"is_active": true}	{"is_active": false}	\N	442	2026-07-07 16:36:36.522048-06	2026-07-07 16:36:36.522048-06
\N	client.deactivated	clients	76	{"is_active": true}	{"is_active": false}	\N	443	2026-07-07 16:36:36.531574-06	2026-07-07 16:36:36.531574-06
\N	client.updated	clients	22	{"client_type": "persona_moral", "legal_name": "Aeroplasa de Occidente, S.A. de C.V.", "commercial_name": "Aeroplasa de Occidente, S.A. de C.V.", "rfc": null, "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "gteservicio@aeroplasadeoccidente.com", "phone": "+52 311 270 3229", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "Av. Insurgentes Poniente S/N", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "Tepic", "city": "Tepic", "state": "Nayarit", "postal_code": "63000", "country": "Mexico", "fiscal_postal_code": "63000", "contacts": []}	{"client_type": "persona_moral", "legal_name": "Aeroplasa de Occidente, S.A. de C.V.", "commercial_name": "Aeroplasa de Occidente, S.A. de C.V.", "rfc": "XAXX010101000", "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "gteservicio@aeroplasadeoccidente.com", "phone": "+52 311 270 3229", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "Av. Insurgentes Poniente S/N", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "Tepic", "city": "Tepic", "state": "Nayarit", "postal_code": "63000", "country": "Mexico", "fiscal_postal_code": "63000", "contacts": []}	\N	381	2026-07-07 14:36:28.548255-06	2026-07-07 14:36:28.548255-06
\N	client.updated	clients	4	{"client_type": "persona_moral", "legal_name": "AGRO FRESAM", "commercial_name": "AGRO FRESAM", "rfc": null, "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "gestiondelacalidad@agrofresam.com.mx", "phone": "+1 800-890-7825", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "BACHILLERES 39 EJIDAL", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "JACONA", "city": "JACONA", "state": "Michoac\\u00e1n", "postal_code": "59893", "country": "Mexico", "fiscal_postal_code": "59893", "contacts": []}	{"client_type": "persona_moral", "legal_name": "AGRO FRESAM", "commercial_name": "AGRO FRESAM", "rfc": "XAXX010101000", "curp": null, "first_name": null, "first_last_name": null, "second_last_name": null, "email": "gestiondelacalidad@agrofresam.com.mx", "phone": "+1 800-890-7825", "tax_regime": "General de Ley de Personas Morales", "cfdi_use": null, "street_type": null, "street": "BACHILLERES 39 EJIDAL", "exterior_number": null, "interior_number": null, "neighborhood": null, "locality": null, "municipality": "JACONA", "city": "JACONA", "state": "Michoac\\u00e1n", "postal_code": "59893", "country": "Mexico", "fiscal_postal_code": "59893", "contacts": []}	\N	382	2026-07-07 14:36:30.432006-06	2026-07-07 14:36:30.432006-06
\N	client.deactivated	clients	2	{"is_active": true}	{"is_active": false}	\N	383	2026-07-07 16:36:32.153552-06	2026-07-07 16:36:32.153552-06
\N	client.deactivated	clients	21	{"is_active": true}	{"is_active": false}	\N	384	2026-07-07 16:36:32.188743-06	2026-07-07 16:36:32.188743-06
\N	client.deactivated	clients	3	{"is_active": true}	{"is_active": false}	\N	385	2026-07-07 16:36:32.204528-06	2026-07-07 16:36:32.204528-06
\N	client.deactivated	clients	22	{"is_active": true}	{"is_active": false}	\N	386	2026-07-07 16:36:32.217646-06	2026-07-07 16:36:32.217646-06
\N	client.deactivated	clients	4	{"is_active": true}	{"is_active": false}	\N	387	2026-07-07 16:36:32.229975-06	2026-07-07 16:36:32.229975-06
\N	client.deactivated	clients	23	{"is_active": true}	{"is_active": false}	\N	388	2026-07-07 16:36:32.242257-06	2026-07-07 16:36:32.242257-06
\N	client.deactivated	clients	5	{"is_active": true}	{"is_active": false}	\N	389	2026-07-07 16:36:32.254591-06	2026-07-07 16:36:32.254591-06
\N	client.deactivated	clients	24	{"is_active": true}	{"is_active": false}	\N	390	2026-07-07 16:36:32.266543-06	2026-07-07 16:36:32.266543-06
\N	client.deactivated	clients	6	{"is_active": true}	{"is_active": false}	\N	391	2026-07-07 16:36:32.279469-06	2026-07-07 16:36:32.279469-06
\N	client.deactivated	clients	25	{"is_active": true}	{"is_active": false}	\N	392	2026-07-07 16:36:32.290686-06	2026-07-07 16:36:32.290686-06
\N	client.deactivated	clients	26	{"is_active": true}	{"is_active": false}	\N	393	2026-07-07 16:36:32.30418-06	2026-07-07 16:36:32.30418-06
\N	client.deactivated	clients	27	{"is_active": true}	{"is_active": false}	\N	394	2026-07-07 16:36:32.315052-06	2026-07-07 16:36:32.315052-06
\N	client.deactivated	clients	7	{"is_active": true}	{"is_active": false}	\N	395	2026-07-07 16:36:32.328115-06	2026-07-07 16:36:32.328115-06
\N	client.deactivated	clients	8	{"is_active": true}	{"is_active": false}	\N	396	2026-07-07 16:36:32.339356-06	2026-07-07 16:36:32.339356-06
\N	client.deactivated	clients	9	{"is_active": true}	{"is_active": false}	\N	397	2026-07-07 16:36:32.350041-06	2026-07-07 16:36:32.350041-06
\N	client.deactivated	clients	11	{"is_active": true}	{"is_active": false}	\N	398	2026-07-07 16:36:32.361834-06	2026-07-07 16:36:32.361834-06
\N	client.deactivated	clients	28	{"is_active": true}	{"is_active": false}	\N	399	2026-07-07 16:36:32.376051-06	2026-07-07 16:36:32.376051-06
\N	client.deactivated	clients	361	{"is_active": true}	{"is_active": false}	\N	400	2026-07-07 16:36:32.387786-06	2026-07-07 16:36:32.387786-06
\N	client.deactivated	clients	29	{"is_active": true}	{"is_active": false}	\N	401	2026-07-07 16:36:32.399727-06	2026-07-07 16:36:32.399727-06
\N	client.deactivated	clients	12	{"is_active": true}	{"is_active": false}	\N	402	2026-07-07 16:36:32.412069-06	2026-07-07 16:36:32.412069-06
\N	client.deactivated	clients	13	{"is_active": true}	{"is_active": false}	\N	403	2026-07-07 16:36:32.422102-06	2026-07-07 16:36:32.422102-06
\N	client.deactivated	clients	30	{"is_active": true}	{"is_active": false}	\N	404	2026-07-07 16:36:32.433741-06	2026-07-07 16:36:32.433741-06
\N	client.deactivated	clients	14	{"is_active": true}	{"is_active": false}	\N	405	2026-07-07 16:36:32.44419-06	2026-07-07 16:36:32.44419-06
\N	client.deactivated	clients	15	{"is_active": true}	{"is_active": false}	\N	406	2026-07-07 16:36:32.4551-06	2026-07-07 16:36:32.4551-06
\N	client.deactivated	clients	31	{"is_active": true}	{"is_active": false}	\N	407	2026-07-07 16:36:32.464307-06	2026-07-07 16:36:32.464307-06
\N	client.deactivated	clients	32	{"is_active": true}	{"is_active": false}	\N	408	2026-07-07 16:36:32.476539-06	2026-07-07 16:36:32.476539-06
\N	client.deactivated	clients	16	{"is_active": true}	{"is_active": false}	\N	409	2026-07-07 16:36:32.49153-06	2026-07-07 16:36:32.49153-06
\N	client.deactivated	clients	17	{"is_active": true}	{"is_active": false}	\N	410	2026-07-07 16:36:32.504342-06	2026-07-07 16:36:32.504342-06
\N	client.deactivated	clients	18	{"is_active": true}	{"is_active": false}	\N	411	2026-07-07 16:36:32.517891-06	2026-07-07 16:36:32.517891-06
\N	client.deactivated	clients	33	{"is_active": true}	{"is_active": false}	\N	412	2026-07-07 16:36:32.531535-06	2026-07-07 16:36:32.531535-06
\N	client.deactivated	clients	19	{"is_active": true}	{"is_active": false}	\N	413	2026-07-07 16:36:32.543311-06	2026-07-07 16:36:32.543311-06
\N	client.deactivated	clients	10	{"is_active": true}	{"is_active": false}	\N	414	2026-07-07 16:36:32.555781-06	2026-07-07 16:36:32.555781-06
\N	client.deactivated	clients	20	{"is_active": true}	{"is_active": false}	\N	415	2026-07-07 16:36:32.56908-06	2026-07-07 16:36:32.56908-06
\N	client.deactivated	clients	38	{"is_active": true}	{"is_active": false}	\N	416	2026-07-07 16:36:32.581904-06	2026-07-07 16:36:32.581904-06
\N	client.deactivated	clients	39	{"is_active": true}	{"is_active": false}	\N	417	2026-07-07 16:36:32.595723-06	2026-07-07 16:36:32.595723-06
\N	client.deactivated	clients	40	{"is_active": true}	{"is_active": false}	\N	418	2026-07-07 16:36:32.610306-06	2026-07-07 16:36:32.610306-06
\N	client.deactivated	clients	34	{"is_active": true}	{"is_active": false}	\N	419	2026-07-07 16:36:32.624832-06	2026-07-07 16:36:32.624832-06
\N	client.deactivated	clients	35	{"is_active": true}	{"is_active": false}	\N	420	2026-07-07 16:36:32.637213-06	2026-07-07 16:36:32.637213-06
\N	client.deactivated	clients	36	{"is_active": true}	{"is_active": false}	\N	421	2026-07-07 16:36:32.648176-06	2026-07-07 16:36:32.648176-06
\N	client.deactivated	clients	37	{"is_active": true}	{"is_active": false}	\N	422	2026-07-07 16:36:32.658937-06	2026-07-07 16:36:32.658937-06
\N	client.deactivated	clients	41	{"is_active": true}	{"is_active": false}	\N	423	2026-07-07 16:36:32.669814-06	2026-07-07 16:36:32.669814-06
\N	client.deactivated	clients	42	{"is_active": true}	{"is_active": false}	\N	424	2026-07-07 16:36:32.683081-06	2026-07-07 16:36:32.683081-06
\N	client.deactivated	clients	43	{"is_active": true}	{"is_active": false}	\N	425	2026-07-07 16:36:32.695393-06	2026-07-07 16:36:32.695393-06
\N	client.deactivated	clients	66	{"is_active": true}	{"is_active": false}	\N	426	2026-07-07 16:36:32.705923-06	2026-07-07 16:36:32.705923-06
\N	client.deactivated	clients	44	{"is_active": true}	{"is_active": false}	\N	427	2026-07-07 16:36:32.719541-06	2026-07-07 16:36:32.719541-06
\N	client.deactivated	clients	67	{"is_active": true}	{"is_active": false}	\N	428	2026-07-07 16:36:32.733581-06	2026-07-07 16:36:32.733581-06
\N	client.deactivated	clients	68	{"is_active": true}	{"is_active": false}	\N	429	2026-07-07 16:36:32.746341-06	2026-07-07 16:36:32.746341-06
\N	client.deactivated	clients	69	{"is_active": true}	{"is_active": false}	\N	430	2026-07-07 16:36:32.75947-06	2026-07-07 16:36:32.75947-06
\N	client.deactivated	clients	70	{"is_active": true}	{"is_active": false}	\N	431	2026-07-07 16:36:32.773936-06	2026-07-07 16:36:32.773936-06
\N	client.deactivated	clients	45	{"is_active": true}	{"is_active": false}	\N	432	2026-07-07 16:36:32.784169-06	2026-07-07 16:36:32.784169-06
\N	client.deactivated	clients	71	{"is_active": true}	{"is_active": false}	\N	433	2026-07-07 16:36:36.41021-06	2026-07-07 16:36:36.41021-06
\N	client.deactivated	clients	50	{"is_active": true}	{"is_active": false}	\N	444	2026-07-07 16:36:36.543112-06	2026-07-07 16:36:36.543112-06
\N	client.deactivated	clients	51	{"is_active": true}	{"is_active": false}	\N	445	2026-07-07 16:36:36.554116-06	2026-07-07 16:36:36.554116-06
\N	client.deactivated	clients	77	{"is_active": true}	{"is_active": false}	\N	446	2026-07-07 16:36:36.563455-06	2026-07-07 16:36:36.563455-06
\N	client.deactivated	clients	52	{"is_active": true}	{"is_active": false}	\N	447	2026-07-07 16:36:36.574535-06	2026-07-07 16:36:36.574535-06
\N	client.deactivated	clients	78	{"is_active": true}	{"is_active": false}	\N	448	2026-07-07 16:36:36.586011-06	2026-07-07 16:36:36.586011-06
\N	client.deactivated	clients	79	{"is_active": true}	{"is_active": false}	\N	449	2026-07-07 16:36:36.595534-06	2026-07-07 16:36:36.595534-06
\N	client.deactivated	clients	80	{"is_active": true}	{"is_active": false}	\N	450	2026-07-07 16:36:36.606153-06	2026-07-07 16:36:36.606153-06
\N	client.deactivated	clients	81	{"is_active": true}	{"is_active": false}	\N	451	2026-07-07 16:36:36.616797-06	2026-07-07 16:36:36.616797-06
\N	client.deactivated	clients	82	{"is_active": true}	{"is_active": false}	\N	452	2026-07-07 16:36:36.626591-06	2026-07-07 16:36:36.626591-06
\N	client.deactivated	clients	83	{"is_active": true}	{"is_active": false}	\N	453	2026-07-07 16:36:36.637243-06	2026-07-07 16:36:36.637243-06
\N	client.deactivated	clients	84	{"is_active": true}	{"is_active": false}	\N	454	2026-07-07 16:36:36.64682-06	2026-07-07 16:36:36.64682-06
\N	client.deactivated	clients	85	{"is_active": true}	{"is_active": false}	\N	455	2026-07-07 16:36:36.659125-06	2026-07-07 16:36:36.659125-06
\N	client.deactivated	clients	53	{"is_active": true}	{"is_active": false}	\N	456	2026-07-07 16:36:36.669964-06	2026-07-07 16:36:36.669964-06
\N	client.deactivated	clients	54	{"is_active": true}	{"is_active": false}	\N	457	2026-07-07 16:36:36.67971-06	2026-07-07 16:36:36.67971-06
\N	client.deactivated	clients	55	{"is_active": true}	{"is_active": false}	\N	458	2026-07-07 16:36:36.691574-06	2026-07-07 16:36:36.691574-06
\N	client.deactivated	clients	56	{"is_active": true}	{"is_active": false}	\N	459	2026-07-07 16:36:36.703636-06	2026-07-07 16:36:36.703636-06
\N	client.deactivated	clients	57	{"is_active": true}	{"is_active": false}	\N	460	2026-07-07 16:36:36.71338-06	2026-07-07 16:36:36.71338-06
\N	client.deactivated	clients	58	{"is_active": true}	{"is_active": false}	\N	461	2026-07-07 16:36:36.724882-06	2026-07-07 16:36:36.724882-06
\N	client.deactivated	clients	86	{"is_active": true}	{"is_active": false}	\N	462	2026-07-07 16:36:36.736138-06	2026-07-07 16:36:36.736138-06
\N	client.deactivated	clients	87	{"is_active": true}	{"is_active": false}	\N	463	2026-07-07 16:36:36.746299-06	2026-07-07 16:36:36.746299-06
\N	client.deactivated	clients	59	{"is_active": true}	{"is_active": false}	\N	464	2026-07-07 16:36:36.762136-06	2026-07-07 16:36:36.762136-06
\N	client.deactivated	clients	88	{"is_active": true}	{"is_active": false}	\N	465	2026-07-07 16:36:36.771433-06	2026-07-07 16:36:36.771433-06
\N	client.deactivated	clients	60	{"is_active": true}	{"is_active": false}	\N	466	2026-07-07 16:36:36.778188-06	2026-07-07 16:36:36.778188-06
\N	client.deactivated	clients	61	{"is_active": true}	{"is_active": false}	\N	467	2026-07-07 16:36:36.786475-06	2026-07-07 16:36:36.786475-06
\N	client.deactivated	clients	62	{"is_active": true}	{"is_active": false}	\N	468	2026-07-07 16:36:36.793027-06	2026-07-07 16:36:36.793027-06
\N	client.deactivated	clients	89	{"is_active": true}	{"is_active": false}	\N	469	2026-07-07 16:36:36.799908-06	2026-07-07 16:36:36.799908-06
\N	client.deactivated	clients	90	{"is_active": true}	{"is_active": false}	\N	470	2026-07-07 16:36:36.808923-06	2026-07-07 16:36:36.808923-06
\N	client.deactivated	clients	63	{"is_active": true}	{"is_active": false}	\N	471	2026-07-07 16:36:36.819531-06	2026-07-07 16:36:36.819531-06
\N	client.deactivated	clients	64	{"is_active": true}	{"is_active": false}	\N	472	2026-07-07 16:36:36.834088-06	2026-07-07 16:36:36.834088-06
\N	client.deactivated	clients	65	{"is_active": true}	{"is_active": false}	\N	473	2026-07-07 16:36:36.84651-06	2026-07-07 16:36:36.84651-06
\N	client.deactivated	clients	93	{"is_active": true}	{"is_active": false}	\N	474	2026-07-07 16:36:36.857791-06	2026-07-07 16:36:36.857791-06
\N	client.deactivated	clients	363	{"is_active": true}	{"is_active": false}	\N	475	2026-07-07 16:36:36.871795-06	2026-07-07 16:36:36.871795-06
\N	client.deactivated	clients	91	{"is_active": true}	{"is_active": false}	\N	476	2026-07-07 16:36:36.884571-06	2026-07-07 16:36:36.884571-06
\N	client.deactivated	clients	94	{"is_active": true}	{"is_active": false}	\N	477	2026-07-07 16:36:36.893214-06	2026-07-07 16:36:36.893214-06
\N	client.deactivated	clients	92	{"is_active": true}	{"is_active": false}	\N	478	2026-07-07 16:36:36.904065-06	2026-07-07 16:36:36.904065-06
\N	client.deactivated	clients	99	{"is_active": true}	{"is_active": false}	\N	479	2026-07-07 16:36:36.918626-06	2026-07-07 16:36:36.918626-06
\N	client.deactivated	clients	95	{"is_active": true}	{"is_active": false}	\N	480	2026-07-07 16:36:36.933795-06	2026-07-07 16:36:36.933795-06
\N	client.deactivated	clients	100	{"is_active": true}	{"is_active": false}	\N	481	2026-07-07 16:36:36.946689-06	2026-07-07 16:36:36.946689-06
\N	client.deactivated	clients	96	{"is_active": true}	{"is_active": false}	\N	482	2026-07-07 16:36:36.961039-06	2026-07-07 16:36:36.961039-06
\N	client.deactivated	clients	101	{"is_active": true}	{"is_active": false}	\N	483	2026-07-07 16:36:40.202658-06	2026-07-07 16:36:40.202658-06
\N	client.deactivated	clients	102	{"is_active": true}	{"is_active": false}	\N	484	2026-07-07 16:36:40.219415-06	2026-07-07 16:36:40.219415-06
\N	client.deactivated	clients	103	{"is_active": true}	{"is_active": false}	\N	485	2026-07-07 16:36:40.238341-06	2026-07-07 16:36:40.238341-06
\N	client.deactivated	clients	97	{"is_active": true}	{"is_active": false}	\N	486	2026-07-07 16:36:40.25188-06	2026-07-07 16:36:40.25188-06
\N	client.deactivated	clients	104	{"is_active": true}	{"is_active": false}	\N	487	2026-07-07 16:36:40.262421-06	2026-07-07 16:36:40.262421-06
\N	client.deactivated	clients	105	{"is_active": true}	{"is_active": false}	\N	488	2026-07-07 16:36:40.274223-06	2026-07-07 16:36:40.274223-06
\N	client.deactivated	clients	98	{"is_active": true}	{"is_active": false}	\N	489	2026-07-07 16:36:40.285438-06	2026-07-07 16:36:40.285438-06
\N	client.deactivated	clients	106	{"is_active": true}	{"is_active": false}	\N	490	2026-07-07 16:36:40.296028-06	2026-07-07 16:36:40.296028-06
\N	client.deactivated	clients	107	{"is_active": true}	{"is_active": false}	\N	491	2026-07-07 16:36:40.304922-06	2026-07-07 16:36:40.304922-06
\N	client.deactivated	clients	123	{"is_active": true}	{"is_active": false}	\N	492	2026-07-07 16:36:40.315428-06	2026-07-07 16:36:40.315428-06
\N	client.deactivated	clients	124	{"is_active": true}	{"is_active": false}	\N	493	2026-07-07 16:36:40.326664-06	2026-07-07 16:36:40.326664-06
\N	client.deactivated	clients	108	{"is_active": true}	{"is_active": false}	\N	494	2026-07-07 16:36:40.337792-06	2026-07-07 16:36:40.337792-06
\N	client.deactivated	clients	109	{"is_active": true}	{"is_active": false}	\N	495	2026-07-07 16:36:40.34666-06	2026-07-07 16:36:40.34666-06
\N	client.deactivated	clients	125	{"is_active": true}	{"is_active": false}	\N	496	2026-07-07 16:36:40.357759-06	2026-07-07 16:36:40.357759-06
\N	client.deactivated	clients	110	{"is_active": true}	{"is_active": false}	\N	497	2026-07-07 16:36:40.369306-06	2026-07-07 16:36:40.369306-06
\N	client.deactivated	clients	111	{"is_active": true}	{"is_active": false}	\N	498	2026-07-07 16:36:40.378706-06	2026-07-07 16:36:40.378706-06
\N	client.deactivated	clients	112	{"is_active": true}	{"is_active": false}	\N	499	2026-07-07 16:36:40.38986-06	2026-07-07 16:36:40.38986-06
\N	client.deactivated	clients	113	{"is_active": true}	{"is_active": false}	\N	500	2026-07-07 16:36:40.400089-06	2026-07-07 16:36:40.400089-06
\N	client.deactivated	clients	114	{"is_active": true}	{"is_active": false}	\N	501	2026-07-07 16:36:40.414015-06	2026-07-07 16:36:40.414015-06
\N	client.deactivated	clients	126	{"is_active": true}	{"is_active": false}	\N	502	2026-07-07 16:36:40.426516-06	2026-07-07 16:36:40.426516-06
\N	client.deactivated	clients	115	{"is_active": true}	{"is_active": false}	\N	503	2026-07-07 16:36:40.438348-06	2026-07-07 16:36:40.438348-06
\N	client.deactivated	clients	116	{"is_active": true}	{"is_active": false}	\N	504	2026-07-07 16:36:40.449202-06	2026-07-07 16:36:40.449202-06
\N	client.deactivated	clients	117	{"is_active": true}	{"is_active": false}	\N	505	2026-07-07 16:36:40.462369-06	2026-07-07 16:36:40.462369-06
\N	client.deactivated	clients	127	{"is_active": true}	{"is_active": false}	\N	506	2026-07-07 16:36:40.475926-06	2026-07-07 16:36:40.475926-06
\N	client.deactivated	clients	128	{"is_active": true}	{"is_active": false}	\N	507	2026-07-07 16:36:40.489789-06	2026-07-07 16:36:40.489789-06
\N	client.deactivated	clients	118	{"is_active": true}	{"is_active": false}	\N	508	2026-07-07 16:36:40.503208-06	2026-07-07 16:36:40.503208-06
\N	client.deactivated	clients	129	{"is_active": true}	{"is_active": false}	\N	509	2026-07-07 16:36:40.516802-06	2026-07-07 16:36:40.516802-06
\N	client.deactivated	clients	130	{"is_active": true}	{"is_active": false}	\N	510	2026-07-07 16:36:40.530658-06	2026-07-07 16:36:40.530658-06
\N	client.deactivated	clients	131	{"is_active": true}	{"is_active": false}	\N	511	2026-07-07 16:36:40.542338-06	2026-07-07 16:36:40.542338-06
\N	client.deactivated	clients	132	{"is_active": true}	{"is_active": false}	\N	512	2026-07-07 16:36:40.55344-06	2026-07-07 16:36:40.55344-06
\N	client.deactivated	clients	119	{"is_active": true}	{"is_active": false}	\N	513	2026-07-07 16:36:40.564697-06	2026-07-07 16:36:40.564697-06
\N	client.deactivated	clients	133	{"is_active": true}	{"is_active": false}	\N	514	2026-07-07 16:36:40.576316-06	2026-07-07 16:36:40.576316-06
\N	client.deactivated	clients	134	{"is_active": true}	{"is_active": false}	\N	515	2026-07-07 16:36:40.587202-06	2026-07-07 16:36:40.587202-06
\N	client.deactivated	clients	120	{"is_active": true}	{"is_active": false}	\N	516	2026-07-07 16:36:40.597231-06	2026-07-07 16:36:40.597231-06
\N	client.deactivated	clients	121	{"is_active": true}	{"is_active": false}	\N	517	2026-07-07 16:36:40.609642-06	2026-07-07 16:36:40.609642-06
\N	client.deactivated	clients	122	{"is_active": true}	{"is_active": false}	\N	518	2026-07-07 16:36:40.621168-06	2026-07-07 16:36:40.621168-06
\N	client.deactivated	clients	135	{"is_active": true}	{"is_active": false}	\N	519	2026-07-07 16:36:40.631532-06	2026-07-07 16:36:40.631532-06
\N	client.deactivated	clients	136	{"is_active": true}	{"is_active": false}	\N	520	2026-07-07 16:36:40.642763-06	2026-07-07 16:36:40.642763-06
\N	client.deactivated	clients	140	{"is_active": true}	{"is_active": false}	\N	521	2026-07-07 16:36:40.655325-06	2026-07-07 16:36:40.655325-06
\N	client.deactivated	clients	364	{"is_active": true}	{"is_active": false}	\N	522	2026-07-07 16:36:40.665789-06	2026-07-07 16:36:40.665789-06
\N	client.deactivated	clients	365	{"is_active": true}	{"is_active": false}	\N	523	2026-07-07 16:36:40.67693-06	2026-07-07 16:36:40.67693-06
\N	client.deactivated	clients	141	{"is_active": true}	{"is_active": false}	\N	524	2026-07-07 16:36:40.688908-06	2026-07-07 16:36:40.688908-06
\N	client.deactivated	clients	142	{"is_active": true}	{"is_active": false}	\N	525	2026-07-07 16:36:40.699195-06	2026-07-07 16:36:40.699195-06
\N	client.deactivated	clients	137	{"is_active": true}	{"is_active": false}	\N	526	2026-07-07 16:36:40.710364-06	2026-07-07 16:36:40.710364-06
\N	client.deactivated	clients	138	{"is_active": true}	{"is_active": false}	\N	527	2026-07-07 16:36:40.722955-06	2026-07-07 16:36:40.722955-06
\N	client.deactivated	clients	143	{"is_active": true}	{"is_active": false}	\N	528	2026-07-07 16:36:40.734985-06	2026-07-07 16:36:40.734985-06
\N	client.deactivated	clients	145	{"is_active": true}	{"is_active": false}	\N	529	2026-07-07 16:36:40.745609-06	2026-07-07 16:36:40.745609-06
\N	client.deactivated	clients	146	{"is_active": true}	{"is_active": false}	\N	530	2026-07-07 16:36:40.759156-06	2026-07-07 16:36:40.759156-06
\N	client.deactivated	clients	144	{"is_active": true}	{"is_active": false}	\N	531	2026-07-07 16:36:40.774915-06	2026-07-07 16:36:40.774915-06
\N	client.deactivated	clients	147	{"is_active": true}	{"is_active": false}	\N	532	2026-07-07 16:36:40.788061-06	2026-07-07 16:36:40.788061-06
\N	client.deactivated	clients	139	{"is_active": true}	{"is_active": false}	\N	533	2026-07-07 16:36:43.71397-06	2026-07-07 16:36:43.71397-06
\N	client.deactivated	clients	148	{"is_active": true}	{"is_active": false}	\N	534	2026-07-07 16:36:43.730441-06	2026-07-07 16:36:43.730441-06
\N	client.deactivated	clients	155	{"is_active": true}	{"is_active": false}	\N	535	2026-07-07 16:36:43.747622-06	2026-07-07 16:36:43.747622-06
\N	client.deactivated	clients	149	{"is_active": true}	{"is_active": false}	\N	536	2026-07-07 16:36:43.762233-06	2026-07-07 16:36:43.762233-06
\N	client.deactivated	clients	150	{"is_active": true}	{"is_active": false}	\N	537	2026-07-07 16:36:43.775188-06	2026-07-07 16:36:43.775188-06
\N	client.deactivated	clients	156	{"is_active": true}	{"is_active": false}	\N	538	2026-07-07 16:36:43.78805-06	2026-07-07 16:36:43.78805-06
\N	client.deactivated	clients	157	{"is_active": true}	{"is_active": false}	\N	539	2026-07-07 16:36:43.802334-06	2026-07-07 16:36:43.802334-06
\N	client.deactivated	clients	151	{"is_active": true}	{"is_active": false}	\N	540	2026-07-07 16:36:43.814787-06	2026-07-07 16:36:43.814787-06
\N	client.deactivated	clients	366	{"is_active": true}	{"is_active": false}	\N	541	2026-07-07 16:36:43.8256-06	2026-07-07 16:36:43.8256-06
\N	client.deactivated	clients	158	{"is_active": true}	{"is_active": false}	\N	542	2026-07-07 16:36:43.836679-06	2026-07-07 16:36:43.836679-06
\N	client.deactivated	clients	152	{"is_active": true}	{"is_active": false}	\N	543	2026-07-07 16:36:43.848651-06	2026-07-07 16:36:43.848651-06
\N	client.deactivated	clients	159	{"is_active": true}	{"is_active": false}	\N	544	2026-07-07 16:36:43.859513-06	2026-07-07 16:36:43.859513-06
\N	client.deactivated	clients	153	{"is_active": true}	{"is_active": false}	\N	545	2026-07-07 16:36:43.8716-06	2026-07-07 16:36:43.8716-06
\N	client.deactivated	clients	160	{"is_active": true}	{"is_active": false}	\N	546	2026-07-07 16:36:43.882112-06	2026-07-07 16:36:43.882112-06
\N	client.deactivated	clients	161	{"is_active": true}	{"is_active": false}	\N	547	2026-07-07 16:36:43.894498-06	2026-07-07 16:36:43.894498-06
\N	client.deactivated	clients	162	{"is_active": true}	{"is_active": false}	\N	548	2026-07-07 16:36:43.90614-06	2026-07-07 16:36:43.90614-06
\N	client.deactivated	clients	154	{"is_active": true}	{"is_active": false}	\N	549	2026-07-07 16:36:43.917552-06	2026-07-07 16:36:43.917552-06
\N	client.deactivated	clients	163	{"is_active": true}	{"is_active": false}	\N	550	2026-07-07 16:36:43.930875-06	2026-07-07 16:36:43.930875-06
\N	client.deactivated	clients	164	{"is_active": true}	{"is_active": false}	\N	551	2026-07-07 16:36:43.942217-06	2026-07-07 16:36:43.942217-06
\N	client.deactivated	clients	165	{"is_active": true}	{"is_active": false}	\N	552	2026-07-07 16:36:43.953074-06	2026-07-07 16:36:43.953074-06
\N	client.deactivated	clients	166	{"is_active": true}	{"is_active": false}	\N	553	2026-07-07 16:36:43.964229-06	2026-07-07 16:36:43.964229-06
\N	client.deactivated	clients	167	{"is_active": true}	{"is_active": false}	\N	554	2026-07-07 16:36:43.977395-06	2026-07-07 16:36:43.977395-06
\N	client.deactivated	clients	168	{"is_active": true}	{"is_active": false}	\N	555	2026-07-07 16:36:43.99002-06	2026-07-07 16:36:43.99002-06
\N	client.deactivated	clients	169	{"is_active": true}	{"is_active": false}	\N	556	2026-07-07 16:36:44.001997-06	2026-07-07 16:36:44.001997-06
\N	client.deactivated	clients	170	{"is_active": true}	{"is_active": false}	\N	557	2026-07-07 16:36:44.017244-06	2026-07-07 16:36:44.017244-06
\N	client.deactivated	clients	171	{"is_active": true}	{"is_active": false}	\N	558	2026-07-07 16:36:44.028803-06	2026-07-07 16:36:44.028803-06
\N	client.deactivated	clients	172	{"is_active": true}	{"is_active": false}	\N	559	2026-07-07 16:36:44.040981-06	2026-07-07 16:36:44.040981-06
\N	client.deactivated	clients	181	{"is_active": true}	{"is_active": false}	\N	560	2026-07-07 16:36:44.054603-06	2026-07-07 16:36:44.054603-06
\N	client.deactivated	clients	173	{"is_active": true}	{"is_active": false}	\N	561	2026-07-07 16:36:44.068203-06	2026-07-07 16:36:44.068203-06
\N	client.deactivated	clients	182	{"is_active": true}	{"is_active": false}	\N	562	2026-07-07 16:36:44.080359-06	2026-07-07 16:36:44.080359-06
\N	client.deactivated	clients	174	{"is_active": true}	{"is_active": false}	\N	563	2026-07-07 16:36:44.091349-06	2026-07-07 16:36:44.091349-06
\N	client.deactivated	clients	175	{"is_active": true}	{"is_active": false}	\N	564	2026-07-07 16:36:44.102147-06	2026-07-07 16:36:44.102147-06
\N	client.deactivated	clients	176	{"is_active": true}	{"is_active": false}	\N	565	2026-07-07 16:36:44.11234-06	2026-07-07 16:36:44.11234-06
\N	client.deactivated	clients	183	{"is_active": true}	{"is_active": false}	\N	566	2026-07-07 16:36:44.123705-06	2026-07-07 16:36:44.123705-06
\N	client.deactivated	clients	184	{"is_active": true}	{"is_active": false}	\N	567	2026-07-07 16:36:44.136143-06	2026-07-07 16:36:44.136143-06
\N	client.deactivated	clients	185	{"is_active": true}	{"is_active": false}	\N	568	2026-07-07 16:36:44.14685-06	2026-07-07 16:36:44.14685-06
\N	client.deactivated	clients	177	{"is_active": true}	{"is_active": false}	\N	569	2026-07-07 16:36:44.157858-06	2026-07-07 16:36:44.157858-06
\N	client.deactivated	clients	178	{"is_active": true}	{"is_active": false}	\N	570	2026-07-07 16:36:44.169134-06	2026-07-07 16:36:44.169134-06
\N	client.deactivated	clients	186	{"is_active": true}	{"is_active": false}	\N	571	2026-07-07 16:36:44.18342-06	2026-07-07 16:36:44.18342-06
\N	client.deactivated	clients	179	{"is_active": true}	{"is_active": false}	\N	572	2026-07-07 16:36:44.194939-06	2026-07-07 16:36:44.194939-06
\N	client.deactivated	clients	180	{"is_active": true}	{"is_active": false}	\N	573	2026-07-07 16:36:44.207038-06	2026-07-07 16:36:44.207038-06
\N	client.deactivated	clients	187	{"is_active": true}	{"is_active": false}	\N	574	2026-07-07 16:36:44.220051-06	2026-07-07 16:36:44.220051-06
\N	client.deactivated	clients	191	{"is_active": true}	{"is_active": false}	\N	575	2026-07-07 16:36:44.236204-06	2026-07-07 16:36:44.236204-06
\N	client.deactivated	clients	192	{"is_active": true}	{"is_active": false}	\N	576	2026-07-07 16:36:44.253839-06	2026-07-07 16:36:44.253839-06
\N	client.deactivated	clients	188	{"is_active": true}	{"is_active": false}	\N	577	2026-07-07 16:36:44.269875-06	2026-07-07 16:36:44.269875-06
\N	client.deactivated	clients	193	{"is_active": true}	{"is_active": false}	\N	578	2026-07-07 16:36:44.285748-06	2026-07-07 16:36:44.285748-06
\N	client.deactivated	clients	189	{"is_active": true}	{"is_active": false}	\N	579	2026-07-07 16:36:44.302006-06	2026-07-07 16:36:44.302006-06
\N	client.deactivated	clients	194	{"is_active": true}	{"is_active": false}	\N	580	2026-07-07 16:36:44.319224-06	2026-07-07 16:36:44.319224-06
\N	client.deactivated	clients	367	{"is_active": true}	{"is_active": false}	\N	581	2026-07-07 16:36:44.338368-06	2026-07-07 16:36:44.338368-06
\N	client.deactivated	clients	195	{"is_active": true}	{"is_active": false}	\N	582	2026-07-07 16:36:44.351927-06	2026-07-07 16:36:44.351927-06
\N	client.deactivated	clients	190	{"is_active": true}	{"is_active": false}	\N	583	2026-07-07 16:36:47.780443-06	2026-07-07 16:36:47.780443-06
\N	client.deactivated	clients	197	{"is_active": true}	{"is_active": false}	\N	584	2026-07-07 16:36:47.795587-06	2026-07-07 16:36:47.795587-06
\N	client.deactivated	clients	196	{"is_active": true}	{"is_active": false}	\N	585	2026-07-07 16:36:47.813216-06	2026-07-07 16:36:47.813216-06
\N	client.deactivated	clients	208	{"is_active": true}	{"is_active": false}	\N	586	2026-07-07 16:36:47.828747-06	2026-07-07 16:36:47.828747-06
\N	client.deactivated	clients	198	{"is_active": true}	{"is_active": false}	\N	587	2026-07-07 16:36:47.841742-06	2026-07-07 16:36:47.841742-06
\N	client.deactivated	clients	209	{"is_active": true}	{"is_active": false}	\N	588	2026-07-07 16:36:47.85366-06	2026-07-07 16:36:47.85366-06
\N	client.deactivated	clients	210	{"is_active": true}	{"is_active": false}	\N	589	2026-07-07 16:36:47.86726-06	2026-07-07 16:36:47.86726-06
\N	client.deactivated	clients	211	{"is_active": true}	{"is_active": false}	\N	590	2026-07-07 16:36:47.880672-06	2026-07-07 16:36:47.880672-06
\N	client.deactivated	clients	368	{"is_active": true}	{"is_active": false}	\N	591	2026-07-07 16:36:47.893063-06	2026-07-07 16:36:47.893063-06
\N	client.deactivated	clients	212	{"is_active": true}	{"is_active": false}	\N	592	2026-07-07 16:36:47.906465-06	2026-07-07 16:36:47.906465-06
\N	client.deactivated	clients	213	{"is_active": true}	{"is_active": false}	\N	593	2026-07-07 16:36:47.918875-06	2026-07-07 16:36:47.918875-06
\N	client.deactivated	clients	200	{"is_active": true}	{"is_active": false}	\N	594	2026-07-07 16:36:47.929034-06	2026-07-07 16:36:47.929034-06
\N	client.deactivated	clients	201	{"is_active": true}	{"is_active": false}	\N	595	2026-07-07 16:36:47.940387-06	2026-07-07 16:36:47.940387-06
\N	client.deactivated	clients	202	{"is_active": true}	{"is_active": false}	\N	596	2026-07-07 16:36:47.952518-06	2026-07-07 16:36:47.952518-06
\N	client.deactivated	clients	214	{"is_active": true}	{"is_active": false}	\N	597	2026-07-07 16:36:47.96312-06	2026-07-07 16:36:47.96312-06
\N	client.deactivated	clients	215	{"is_active": true}	{"is_active": false}	\N	598	2026-07-07 16:36:47.974643-06	2026-07-07 16:36:47.974643-06
\N	client.deactivated	clients	203	{"is_active": true}	{"is_active": false}	\N	599	2026-07-07 16:36:47.985554-06	2026-07-07 16:36:47.985554-06
\N	client.deactivated	clients	204	{"is_active": true}	{"is_active": false}	\N	600	2026-07-07 16:36:47.997653-06	2026-07-07 16:36:47.997653-06
\N	client.deactivated	clients	205	{"is_active": true}	{"is_active": false}	\N	601	2026-07-07 16:36:48.008614-06	2026-07-07 16:36:48.008614-06
\N	client.deactivated	clients	206	{"is_active": true}	{"is_active": false}	\N	602	2026-07-07 16:36:48.019672-06	2026-07-07 16:36:48.019672-06
\N	client.deactivated	clients	207	{"is_active": true}	{"is_active": false}	\N	603	2026-07-07 16:36:48.031483-06	2026-07-07 16:36:48.031483-06
\N	client.deactivated	clients	226	{"is_active": true}	{"is_active": false}	\N	604	2026-07-07 16:36:48.042142-06	2026-07-07 16:36:48.042142-06
\N	client.deactivated	clients	227	{"is_active": true}	{"is_active": false}	\N	605	2026-07-07 16:36:48.05463-06	2026-07-07 16:36:48.05463-06
\N	client.deactivated	clients	228	{"is_active": true}	{"is_active": false}	\N	606	2026-07-07 16:36:48.067798-06	2026-07-07 16:36:48.067798-06
\N	client.deactivated	clients	216	{"is_active": true}	{"is_active": false}	\N	607	2026-07-07 16:36:48.078079-06	2026-07-07 16:36:48.078079-06
\N	client.deactivated	clients	217	{"is_active": true}	{"is_active": false}	\N	608	2026-07-07 16:36:48.088346-06	2026-07-07 16:36:48.088346-06
\N	client.deactivated	clients	229	{"is_active": true}	{"is_active": false}	\N	609	2026-07-07 16:36:48.099281-06	2026-07-07 16:36:48.099281-06
\N	client.deactivated	clients	369	{"is_active": true}	{"is_active": false}	\N	610	2026-07-07 16:36:48.111222-06	2026-07-07 16:36:48.111222-06
\N	client.deactivated	clients	230	{"is_active": true}	{"is_active": false}	\N	611	2026-07-07 16:36:48.122295-06	2026-07-07 16:36:48.122295-06
\N	client.deactivated	clients	218	{"is_active": true}	{"is_active": false}	\N	612	2026-07-07 16:36:48.134414-06	2026-07-07 16:36:48.134414-06
\N	client.deactivated	clients	231	{"is_active": true}	{"is_active": false}	\N	613	2026-07-07 16:36:48.144238-06	2026-07-07 16:36:48.144238-06
\N	client.deactivated	clients	232	{"is_active": true}	{"is_active": false}	\N	614	2026-07-07 16:36:48.155375-06	2026-07-07 16:36:48.155375-06
\N	client.deactivated	clients	233	{"is_active": true}	{"is_active": false}	\N	615	2026-07-07 16:36:48.164556-06	2026-07-07 16:36:48.164556-06
\N	client.deactivated	clients	234	{"is_active": true}	{"is_active": false}	\N	616	2026-07-07 16:36:48.175367-06	2026-07-07 16:36:48.175367-06
\N	client.deactivated	clients	235	{"is_active": true}	{"is_active": false}	\N	617	2026-07-07 16:36:48.185778-06	2026-07-07 16:36:48.185778-06
\N	client.deactivated	clients	219	{"is_active": true}	{"is_active": false}	\N	618	2026-07-07 16:36:48.19636-06	2026-07-07 16:36:48.19636-06
\N	client.deactivated	clients	1	{"is_active": true}	{"is_active": false}	\N	619	2026-07-07 16:36:48.205502-06	2026-07-07 16:36:48.205502-06
\N	client.deactivated	clients	236	{"is_active": true}	{"is_active": false}	\N	620	2026-07-07 16:36:48.215289-06	2026-07-07 16:36:48.215289-06
\N	client.deactivated	clients	237	{"is_active": true}	{"is_active": false}	\N	621	2026-07-07 16:36:48.225771-06	2026-07-07 16:36:48.225771-06
\N	client.deactivated	clients	238	{"is_active": true}	{"is_active": false}	\N	622	2026-07-07 16:36:48.236544-06	2026-07-07 16:36:48.236544-06
\N	client.deactivated	clients	220	{"is_active": true}	{"is_active": false}	\N	623	2026-07-07 16:36:48.248918-06	2026-07-07 16:36:48.248918-06
\N	client.deactivated	clients	239	{"is_active": true}	{"is_active": false}	\N	624	2026-07-07 16:36:48.261163-06	2026-07-07 16:36:48.261163-06
\N	client.deactivated	clients	240	{"is_active": true}	{"is_active": false}	\N	625	2026-07-07 16:36:48.272406-06	2026-07-07 16:36:48.272406-06
\N	client.deactivated	clients	221	{"is_active": true}	{"is_active": false}	\N	626	2026-07-07 16:36:48.284747-06	2026-07-07 16:36:48.284747-06
\N	client.deactivated	clients	241	{"is_active": true}	{"is_active": false}	\N	627	2026-07-07 16:36:48.298062-06	2026-07-07 16:36:48.298062-06
\N	client.deactivated	clients	242	{"is_active": true}	{"is_active": false}	\N	628	2026-07-07 16:36:48.309975-06	2026-07-07 16:36:48.309975-06
\N	client.deactivated	clients	222	{"is_active": true}	{"is_active": false}	\N	629	2026-07-07 16:36:48.324126-06	2026-07-07 16:36:48.324126-06
\N	client.deactivated	clients	223	{"is_active": true}	{"is_active": false}	\N	630	2026-07-07 16:36:48.338301-06	2026-07-07 16:36:48.338301-06
\N	client.deactivated	clients	243	{"is_active": true}	{"is_active": false}	\N	631	2026-07-07 16:36:48.353539-06	2026-07-07 16:36:48.353539-06
\N	client.deactivated	clients	244	{"is_active": true}	{"is_active": false}	\N	632	2026-07-07 16:36:48.368779-06	2026-07-07 16:36:48.368779-06
\N	client.deactivated	clients	224	{"is_active": true}	{"is_active": false}	\N	633	2026-07-07 16:36:50.800216-06	2026-07-07 16:36:50.800216-06
\N	client.deactivated	clients	225	{"is_active": true}	{"is_active": false}	\N	634	2026-07-07 16:36:50.815262-06	2026-07-07 16:36:50.815262-06
\N	client.deactivated	clients	245	{"is_active": true}	{"is_active": false}	\N	635	2026-07-07 16:36:50.827008-06	2026-07-07 16:36:50.827008-06
\N	client.deactivated	clients	251	{"is_active": true}	{"is_active": false}	\N	636	2026-07-07 16:36:50.8414-06	2026-07-07 16:36:50.8414-06
\N	client.deactivated	clients	246	{"is_active": true}	{"is_active": false}	\N	637	2026-07-07 16:36:50.855507-06	2026-07-07 16:36:50.855507-06
\N	client.deactivated	clients	252	{"is_active": true}	{"is_active": false}	\N	638	2026-07-07 16:36:50.867734-06	2026-07-07 16:36:50.867734-06
\N	client.deactivated	clients	253	{"is_active": true}	{"is_active": false}	\N	639	2026-07-07 16:36:50.877416-06	2026-07-07 16:36:50.877416-06
\N	client.deactivated	clients	247	{"is_active": true}	{"is_active": false}	\N	640	2026-07-07 16:36:50.89052-06	2026-07-07 16:36:50.89052-06
\N	client.deactivated	clients	248	{"is_active": true}	{"is_active": false}	\N	641	2026-07-07 16:36:50.898088-06	2026-07-07 16:36:50.898088-06
\N	client.deactivated	clients	249	{"is_active": true}	{"is_active": false}	\N	642	2026-07-07 16:36:50.907669-06	2026-07-07 16:36:50.907669-06
\N	client.deactivated	clients	250	{"is_active": true}	{"is_active": false}	\N	643	2026-07-07 16:36:50.918024-06	2026-07-07 16:36:50.918024-06
\N	client.deactivated	clients	254	{"is_active": true}	{"is_active": false}	\N	644	2026-07-07 16:36:50.930028-06	2026-07-07 16:36:50.930028-06
\N	client.deactivated	clients	258	{"is_active": true}	{"is_active": false}	\N	645	2026-07-07 16:36:50.939507-06	2026-07-07 16:36:50.939507-06
\N	client.deactivated	clients	259	{"is_active": true}	{"is_active": false}	\N	646	2026-07-07 16:36:50.947707-06	2026-07-07 16:36:50.947707-06
\N	client.deactivated	clients	260	{"is_active": true}	{"is_active": false}	\N	647	2026-07-07 16:36:50.958131-06	2026-07-07 16:36:50.958131-06
\N	client.deactivated	clients	255	{"is_active": true}	{"is_active": false}	\N	648	2026-07-07 16:36:50.968982-06	2026-07-07 16:36:50.968982-06
\N	client.deactivated	clients	261	{"is_active": true}	{"is_active": false}	\N	649	2026-07-07 16:36:50.979115-06	2026-07-07 16:36:50.979115-06
\N	client.deactivated	clients	256	{"is_active": true}	{"is_active": false}	\N	650	2026-07-07 16:36:50.989981-06	2026-07-07 16:36:50.989981-06
\N	client.deactivated	clients	262	{"is_active": true}	{"is_active": false}	\N	651	2026-07-07 16:36:50.999756-06	2026-07-07 16:36:50.999756-06
\N	client.deactivated	clients	257	{"is_active": true}	{"is_active": false}	\N	652	2026-07-07 16:36:51.013155-06	2026-07-07 16:36:51.013155-06
\N	client.deactivated	clients	263	{"is_active": true}	{"is_active": false}	\N	653	2026-07-07 16:36:51.031369-06	2026-07-07 16:36:51.031369-06
\N	client.deactivated	clients	270	{"is_active": true}	{"is_active": false}	\N	654	2026-07-07 16:36:51.04227-06	2026-07-07 16:36:51.04227-06
\N	client.deactivated	clients	264	{"is_active": true}	{"is_active": false}	\N	655	2026-07-07 16:36:51.053383-06	2026-07-07 16:36:51.053383-06
\N	client.deactivated	clients	271	{"is_active": true}	{"is_active": false}	\N	656	2026-07-07 16:36:51.061129-06	2026-07-07 16:36:51.061129-06
\N	client.deactivated	clients	199	{"is_active": true}	{"is_active": false}	\N	657	2026-07-07 16:36:51.072798-06	2026-07-07 16:36:51.072798-06
\N	client.deactivated	clients	272	{"is_active": true}	{"is_active": false}	\N	658	2026-07-07 16:36:51.081512-06	2026-07-07 16:36:51.081512-06
\N	client.deactivated	clients	273	{"is_active": true}	{"is_active": false}	\N	659	2026-07-07 16:36:51.093297-06	2026-07-07 16:36:51.093297-06
\N	client.deactivated	clients	274	{"is_active": true}	{"is_active": false}	\N	660	2026-07-07 16:36:51.102432-06	2026-07-07 16:36:51.102432-06
\N	client.deactivated	clients	265	{"is_active": true}	{"is_active": false}	\N	661	2026-07-07 16:36:51.112092-06	2026-07-07 16:36:51.112092-06
\N	client.deactivated	clients	266	{"is_active": true}	{"is_active": false}	\N	662	2026-07-07 16:36:51.121746-06	2026-07-07 16:36:51.121746-06
\N	client.deactivated	clients	275	{"is_active": true}	{"is_active": false}	\N	663	2026-07-07 16:36:51.134044-06	2026-07-07 16:36:51.134044-06
\N	client.deactivated	clients	267	{"is_active": true}	{"is_active": false}	\N	664	2026-07-07 16:36:51.143408-06	2026-07-07 16:36:51.143408-06
\N	client.deactivated	clients	268	{"is_active": true}	{"is_active": false}	\N	665	2026-07-07 16:36:51.155285-06	2026-07-07 16:36:51.155285-06
\N	client.deactivated	clients	269	{"is_active": true}	{"is_active": false}	\N	666	2026-07-07 16:36:51.165395-06	2026-07-07 16:36:51.165395-06
\N	client.deactivated	clients	277	{"is_active": true}	{"is_active": false}	\N	667	2026-07-07 16:36:51.176578-06	2026-07-07 16:36:51.176578-06
\N	client.deactivated	clients	278	{"is_active": true}	{"is_active": false}	\N	668	2026-07-07 16:36:51.188845-06	2026-07-07 16:36:51.188845-06
\N	client.deactivated	clients	276	{"is_active": true}	{"is_active": false}	\N	669	2026-07-07 16:36:51.199251-06	2026-07-07 16:36:51.199251-06
\N	client.deactivated	clients	283	{"is_active": true}	{"is_active": false}	\N	670	2026-07-07 16:36:51.212426-06	2026-07-07 16:36:51.212426-06
\N	client.deactivated	clients	279	{"is_active": true}	{"is_active": false}	\N	671	2026-07-07 16:36:51.224202-06	2026-07-07 16:36:51.224202-06
\N	client.deactivated	clients	280	{"is_active": true}	{"is_active": false}	\N	672	2026-07-07 16:36:51.234905-06	2026-07-07 16:36:51.234905-06
\N	client.deactivated	clients	284	{"is_active": true}	{"is_active": false}	\N	673	2026-07-07 16:36:51.24554-06	2026-07-07 16:36:51.24554-06
\N	client.deactivated	clients	285	{"is_active": true}	{"is_active": false}	\N	674	2026-07-07 16:36:51.259721-06	2026-07-07 16:36:51.259721-06
\N	client.deactivated	clients	286	{"is_active": true}	{"is_active": false}	\N	675	2026-07-07 16:36:51.273339-06	2026-07-07 16:36:51.273339-06
\N	client.deactivated	clients	281	{"is_active": true}	{"is_active": false}	\N	676	2026-07-07 16:36:51.2855-06	2026-07-07 16:36:51.2855-06
\N	client.deactivated	clients	287	{"is_active": true}	{"is_active": false}	\N	677	2026-07-07 16:36:51.299491-06	2026-07-07 16:36:51.299491-06
\N	client.deactivated	clients	288	{"is_active": true}	{"is_active": false}	\N	678	2026-07-07 16:36:51.313383-06	2026-07-07 16:36:51.313383-06
\N	client.deactivated	clients	282	{"is_active": true}	{"is_active": false}	\N	679	2026-07-07 16:36:51.325634-06	2026-07-07 16:36:51.325634-06
\N	client.deactivated	clients	308	{"is_active": true}	{"is_active": false}	\N	680	2026-07-07 16:36:51.340152-06	2026-07-07 16:36:51.340152-06
\N	client.deactivated	clients	289	{"is_active": true}	{"is_active": false}	\N	681	2026-07-07 16:36:51.352873-06	2026-07-07 16:36:51.352873-06
\N	client.deactivated	clients	290	{"is_active": true}	{"is_active": false}	\N	682	2026-07-07 16:36:51.368178-06	2026-07-07 16:36:51.368178-06
\N	client.deactivated	clients	291	{"is_active": true}	{"is_active": false}	\N	683	2026-07-07 16:36:54.079085-06	2026-07-07 16:36:54.079085-06
\N	client.deactivated	clients	329	{"is_active": true}	{"is_active": false}	\N	684	2026-07-07 16:36:54.094901-06	2026-07-07 16:36:54.094901-06
\N	client.deactivated	clients	292	{"is_active": true}	{"is_active": false}	\N	685	2026-07-07 16:36:54.111045-06	2026-07-07 16:36:54.111045-06
\N	client.deactivated	clients	309	{"is_active": true}	{"is_active": false}	\N	686	2026-07-07 16:36:54.126134-06	2026-07-07 16:36:54.126134-06
\N	client.deactivated	clients	310	{"is_active": true}	{"is_active": false}	\N	687	2026-07-07 16:36:54.137302-06	2026-07-07 16:36:54.137302-06
\N	client.deactivated	clients	311	{"is_active": true}	{"is_active": false}	\N	688	2026-07-07 16:36:54.146073-06	2026-07-07 16:36:54.146073-06
\N	client.deactivated	clients	293	{"is_active": true}	{"is_active": false}	\N	689	2026-07-07 16:36:54.155254-06	2026-07-07 16:36:54.155254-06
\N	client.deactivated	clients	312	{"is_active": true}	{"is_active": false}	\N	690	2026-07-07 16:36:54.162585-06	2026-07-07 16:36:54.162585-06
\N	client.deactivated	clients	313	{"is_active": true}	{"is_active": false}	\N	691	2026-07-07 16:36:54.173002-06	2026-07-07 16:36:54.173002-06
\N	client.deactivated	clients	294	{"is_active": true}	{"is_active": false}	\N	692	2026-07-07 16:36:54.182815-06	2026-07-07 16:36:54.182815-06
\N	client.deactivated	clients	295	{"is_active": true}	{"is_active": false}	\N	693	2026-07-07 16:36:54.192569-06	2026-07-07 16:36:54.192569-06
\N	client.deactivated	clients	314	{"is_active": true}	{"is_active": false}	\N	694	2026-07-07 16:36:54.204676-06	2026-07-07 16:36:54.204676-06
\N	client.deactivated	clients	315	{"is_active": true}	{"is_active": false}	\N	695	2026-07-07 16:36:54.215873-06	2026-07-07 16:36:54.215873-06
\N	client.deactivated	clients	370	{"is_active": true}	{"is_active": false}	\N	696	2026-07-07 16:36:54.225818-06	2026-07-07 16:36:54.225818-06
\N	client.deactivated	clients	316	{"is_active": true}	{"is_active": false}	\N	697	2026-07-07 16:36:54.236442-06	2026-07-07 16:36:54.236442-06
\N	client.deactivated	clients	296	{"is_active": true}	{"is_active": false}	\N	698	2026-07-07 16:36:54.247739-06	2026-07-07 16:36:54.247739-06
\N	client.deactivated	clients	317	{"is_active": true}	{"is_active": false}	\N	699	2026-07-07 16:36:54.257838-06	2026-07-07 16:36:54.257838-06
\N	client.deactivated	clients	318	{"is_active": true}	{"is_active": false}	\N	700	2026-07-07 16:36:54.267987-06	2026-07-07 16:36:54.267987-06
\N	client.deactivated	clients	319	{"is_active": true}	{"is_active": false}	\N	701	2026-07-07 16:36:54.27802-06	2026-07-07 16:36:54.27802-06
\N	client.deactivated	clients	297	{"is_active": true}	{"is_active": false}	\N	702	2026-07-07 16:36:54.290278-06	2026-07-07 16:36:54.290278-06
\N	client.deactivated	clients	320	{"is_active": true}	{"is_active": false}	\N	703	2026-07-07 16:36:54.300763-06	2026-07-07 16:36:54.300763-06
\N	client.deactivated	clients	321	{"is_active": true}	{"is_active": false}	\N	704	2026-07-07 16:36:54.310646-06	2026-07-07 16:36:54.310646-06
\N	client.deactivated	clients	322	{"is_active": true}	{"is_active": false}	\N	705	2026-07-07 16:36:54.322302-06	2026-07-07 16:36:54.322302-06
\N	client.deactivated	clients	323	{"is_active": true}	{"is_active": false}	\N	706	2026-07-07 16:36:54.33191-06	2026-07-07 16:36:54.33191-06
\N	client.deactivated	clients	298	{"is_active": true}	{"is_active": false}	\N	707	2026-07-07 16:36:54.342386-06	2026-07-07 16:36:54.342386-06
\N	client.deactivated	clients	324	{"is_active": true}	{"is_active": false}	\N	708	2026-07-07 16:36:54.353556-06	2026-07-07 16:36:54.353556-06
\N	client.deactivated	clients	299	{"is_active": true}	{"is_active": false}	\N	709	2026-07-07 16:36:54.366415-06	2026-07-07 16:36:54.366415-06
\N	client.deactivated	clients	300	{"is_active": true}	{"is_active": false}	\N	710	2026-07-07 16:36:54.377559-06	2026-07-07 16:36:54.377559-06
\N	client.deactivated	clients	325	{"is_active": true}	{"is_active": false}	\N	711	2026-07-07 16:36:54.389376-06	2026-07-07 16:36:54.389376-06
\N	client.deactivated	clients	326	{"is_active": true}	{"is_active": false}	\N	712	2026-07-07 16:36:54.401369-06	2026-07-07 16:36:54.401369-06
\N	client.deactivated	clients	371	{"is_active": true}	{"is_active": false}	\N	713	2026-07-07 16:36:54.412842-06	2026-07-07 16:36:54.412842-06
\N	client.deactivated	clients	301	{"is_active": true}	{"is_active": false}	\N	714	2026-07-07 16:36:54.423566-06	2026-07-07 16:36:54.423566-06
\N	client.deactivated	clients	302	{"is_active": true}	{"is_active": false}	\N	715	2026-07-07 16:36:54.434529-06	2026-07-07 16:36:54.434529-06
\N	client.deactivated	clients	303	{"is_active": true}	{"is_active": false}	\N	716	2026-07-07 16:36:54.446075-06	2026-07-07 16:36:54.446075-06
\N	client.deactivated	clients	304	{"is_active": true}	{"is_active": false}	\N	717	2026-07-07 16:36:54.457413-06	2026-07-07 16:36:54.457413-06
\N	client.deactivated	clients	305	{"is_active": true}	{"is_active": false}	\N	718	2026-07-07 16:36:54.469397-06	2026-07-07 16:36:54.469397-06
\N	client.deactivated	clients	306	{"is_active": true}	{"is_active": false}	\N	719	2026-07-07 16:36:54.479615-06	2026-07-07 16:36:54.479615-06
\N	client.deactivated	clients	327	{"is_active": true}	{"is_active": false}	\N	720	2026-07-07 16:36:54.492537-06	2026-07-07 16:36:54.492537-06
\N	client.deactivated	clients	328	{"is_active": true}	{"is_active": false}	\N	721	2026-07-07 16:36:54.503461-06	2026-07-07 16:36:54.503461-06
\N	client.deactivated	clients	307	{"is_active": true}	{"is_active": false}	\N	722	2026-07-07 16:36:54.513037-06	2026-07-07 16:36:54.513037-06
\N	client.deactivated	clients	330	{"is_active": true}	{"is_active": false}	\N	723	2026-07-07 16:36:54.525463-06	2026-07-07 16:36:54.525463-06
\N	client.deactivated	clients	337	{"is_active": true}	{"is_active": false}	\N	724	2026-07-07 16:36:54.537668-06	2026-07-07 16:36:54.537668-06
\N	client.deactivated	clients	331	{"is_active": true}	{"is_active": false}	\N	725	2026-07-07 16:36:54.548994-06	2026-07-07 16:36:54.548994-06
\N	client.deactivated	clients	332	{"is_active": true}	{"is_active": false}	\N	726	2026-07-07 16:36:54.562633-06	2026-07-07 16:36:54.562633-06
\N	client.deactivated	clients	338	{"is_active": true}	{"is_active": false}	\N	727	2026-07-07 16:36:54.575625-06	2026-07-07 16:36:54.575625-06
\N	client.deactivated	clients	339	{"is_active": true}	{"is_active": false}	\N	728	2026-07-07 16:36:54.588089-06	2026-07-07 16:36:54.588089-06
\N	client.deactivated	clients	333	{"is_active": true}	{"is_active": false}	\N	729	2026-07-07 16:36:54.601123-06	2026-07-07 16:36:54.601123-06
\N	client.deactivated	clients	340	{"is_active": true}	{"is_active": false}	\N	730	2026-07-07 16:36:54.620816-06	2026-07-07 16:36:54.620816-06
\N	client.deactivated	clients	334	{"is_active": true}	{"is_active": false}	\N	731	2026-07-07 16:36:54.639584-06	2026-07-07 16:36:54.639584-06
\N	client.deactivated	clients	335	{"is_active": true}	{"is_active": false}	\N	732	2026-07-07 16:36:54.653994-06	2026-07-07 16:36:54.653994-06
\N	client.deactivated	clients	336	{"is_active": true}	{"is_active": false}	\N	733	2026-07-07 16:36:57.517937-06	2026-07-07 16:36:57.517937-06
\N	client.deactivated	clients	341	{"is_active": true}	{"is_active": false}	\N	734	2026-07-07 16:36:57.53528-06	2026-07-07 16:36:57.53528-06
\N	client.deactivated	clients	342	{"is_active": true}	{"is_active": false}	\N	735	2026-07-07 16:36:57.553249-06	2026-07-07 16:36:57.553249-06
\N	client.deactivated	clients	343	{"is_active": true}	{"is_active": false}	\N	736	2026-07-07 16:36:57.569246-06	2026-07-07 16:36:57.569246-06
\N	client.deactivated	clients	344	{"is_active": true}	{"is_active": false}	\N	737	2026-07-07 16:36:57.582098-06	2026-07-07 16:36:57.582098-06
\N	client.deactivated	clients	345	{"is_active": true}	{"is_active": false}	\N	738	2026-07-07 16:36:57.595046-06	2026-07-07 16:36:57.595046-06
\N	client.deactivated	clients	352	{"is_active": true}	{"is_active": false}	\N	739	2026-07-07 16:36:57.61126-06	2026-07-07 16:36:57.61126-06
\N	client.deactivated	clients	347	{"is_active": true}	{"is_active": false}	\N	740	2026-07-07 16:36:57.623911-06	2026-07-07 16:36:57.623911-06
\N	client.deactivated	clients	346	{"is_active": true}	{"is_active": false}	\N	741	2026-07-07 16:36:57.635882-06	2026-07-07 16:36:57.635882-06
\N	client.deactivated	clients	348	{"is_active": true}	{"is_active": false}	\N	742	2026-07-07 16:36:57.648508-06	2026-07-07 16:36:57.648508-06
\N	client.deactivated	clients	349	{"is_active": true}	{"is_active": false}	\N	743	2026-07-07 16:36:57.661045-06	2026-07-07 16:36:57.661045-06
\N	client.deactivated	clients	351	{"is_active": true}	{"is_active": false}	\N	744	2026-07-07 16:36:57.674581-06	2026-07-07 16:36:57.674581-06
\N	client.deactivated	clients	350	{"is_active": true}	{"is_active": false}	\N	745	2026-07-07 16:36:57.687696-06	2026-07-07 16:36:57.687696-06
\N	client.deactivated	clients	372	{"is_active": true}	{"is_active": false}	\N	746	2026-07-07 16:36:57.70095-06	2026-07-07 16:36:57.70095-06
\N	client.deactivated	clients	354	{"is_active": true}	{"is_active": false}	\N	747	2026-07-07 16:36:57.710751-06	2026-07-07 16:36:57.710751-06
\N	client.deactivated	clients	355	{"is_active": true}	{"is_active": false}	\N	748	2026-07-07 16:36:57.7216-06	2026-07-07 16:36:57.7216-06
\N	client.deactivated	clients	353	{"is_active": true}	{"is_active": false}	\N	749	2026-07-07 16:36:57.734436-06	2026-07-07 16:36:57.734436-06
\N	client.deactivated	clients	356	{"is_active": true}	{"is_active": false}	\N	750	2026-07-07 16:36:57.744716-06	2026-07-07 16:36:57.744716-06
\N	client.deactivated	clients	357	{"is_active": true}	{"is_active": false}	\N	751	2026-07-07 16:36:57.755554-06	2026-07-07 16:36:57.755554-06
\N	client.deactivated	clients	360	{"is_active": true}	{"is_active": false}	\N	752	2026-07-07 16:36:57.765952-06	2026-07-07 16:36:57.765952-06
\N	client.deactivated	clients	358	{"is_active": true}	{"is_active": false}	\N	753	2026-07-07 16:36:57.77916-06	2026-07-07 16:36:57.77916-06
\N	client.deactivated	clients	359	{"is_active": true}	{"is_active": false}	\N	754	2026-07-07 16:36:57.790714-06	2026-07-07 16:36:57.790714-06
\.


--
-- Data for Name: calibration_procedures; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.calibration_procedures (code, name, description, magnitude, profile_key, version, issuer_company, certificate_type, required_readings, decision_rule, acceptance_criteria, notes, status, is_active, deleted_at, deleted_by, id, created_at, updated_at, uncertainty_model_id, uncertainty_model_version_id) FROM stdin;
\.


--
-- Data for Name: catalog_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.catalog_items (item_type, commodity, category, internal_key, name, description, sat_key, sat_unit, internal_unit, origin_price, origin_currency, exchange_rate, margin_percent, final_price_mxn, internal_cost, cost_currency, calibration_scope, quotation_legend, id, created_at, updated_at, is_active, deleted_at, deleted_by, custom_internal_unit, tax_object, tax_rate) FROM stdin;
\.


--
-- Data for Name: certificates; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.certificates (folio, service_order_id, equipment_id, field_sheet_id, certificate_type, status, issued_on, released_on, title, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, expected_folio, final_pdf_path, final_pdf_original_filename, final_pdf_uploaded_at, final_pdf_uploaded_by_id, capture_started_at, capture_started_by_id, sent_to_quality_at, sent_to_quality_by_id, quality_reviewed_at, quality_reviewed_by_id, quality_rejection_reason, released_to_client_at, released_to_client_by_id, external_source, match_status, match_details, client_visible, authentication_code, authentication_hash, authenticated_pdf_path, authenticated_pdf_generated_at, authenticated_by_id, verification_url) FROM stdin;
\.


--
-- Data for Name: client_contacts; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.client_contacts (client_id, name, email, phone, "position", id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
5	Jorge Rossains	jorgerossains@aguabluerock.com	\N	\N	1	2026-07-07 13:28:01.538702-06	2026-07-07 13:28:01.538702-06	t	\N	\N
13	Sr. Herson Rodríguez	hrodriguez@mulsa.com.mx	+52 392 930 3510	\N	2	2026-07-07 13:28:01.571153-06	2026-07-07 13:28:01.571153-06	t	\N	\N
17	AMAURY ATONDO	a.atondo@autocamiones.mx	+52 697 109 8345	\N	3	2026-07-07 13:28:01.585544-06	2026-07-07 13:28:01.585544-06	t	\N	\N
23	Aurora Lopez	aurora.lopez@agrovetmarket.com.mx	+52 33 3682 2036	\N	5	2026-07-07 13:28:01.608484-06	2026-07-07 13:28:01.608484-06	t	\N	\N
24	Alberto Evangelista	aevangelmx@gmail.com	+52 33 3105 8858	\N	6	2026-07-07 13:28:01.612334-06	2026-07-07 13:28:01.612334-06	t	\N	\N
28	Alberto García	jonathancancino@asesoressire.com.mx	+52 33 3019 4490	\N	7	2026-07-07 13:28:01.627437-06	2026-07-07 13:28:01.627437-06	t	\N	\N
29	Andrea Camarillo	ingvalidacion01@asiip.com.mx	+52 55 2607 9060	\N	8	2026-07-07 13:28:01.630542-06	2026-07-07 13:28:01.630542-06	t	\N	\N
31	Elsa Patricia Torres	auxcalidad@audigalerias.com.mx	\N	\N	9	2026-07-07 13:28:01.637731-06	2026-07-07 13:28:01.637731-06	t	\N	\N
32	Faviola Valenzuela	fvalenzuela@audipatria.mx	+52 33 3648 5650	\N	10	2026-07-07 13:28:01.64213-06	2026-07-07 13:28:01.64213-06	t	\N	\N
35	Marian Rodríguez Laguna	marian.rodriguez@bmcmm.com	+52 81 1022 0042	\N	11	2026-07-07 13:28:01.653692-06	2026-07-07 13:28:01.653692-06	t	\N	\N
38	Ismael Rodriguez	\N	\N	\N	12	2026-07-07 13:28:01.662623-06	2026-07-07 13:28:01.662623-06	t	\N	\N
41	Lic. Sabhat Corpus Nuño	administracion@caycer.com.mx	3 3260 16 58	\N	13	2026-07-07 13:28:01.673308-06	2026-07-07 13:28:01.673308-06	t	\N	\N
50	Mariana Ceja Toscano	mariana.ceja@cfe.mx	\N	\N	14	2026-07-07 13:28:01.702605-06	2026-07-07 13:28:01.702605-06	t	\N	\N
61	Ext. 2148\nBiól. Andrea Ornelas	tecnovigilancia@grupomexlab.com	336342361	\N	15	2026-07-07 13:28:01.732486-06	2026-07-07 13:28:01.732486-06	t	\N	\N
63	Luisa Zalazar	luisa.salazar@craftaviacenter.com	+52 33 2101 1060	\N	16	2026-07-07 13:28:01.738554-06	2026-07-07 13:28:01.738554-06	t	\N	\N
65	Martha Roa	\N	+52 55 4339 5035	\N	17	2026-07-07 13:28:01.744335-06	2026-07-07 13:28:01.744335-06	t	\N	\N
66	Feliper Garcia	\N	+52 921 267 7089	\N	18	2026-07-07 13:28:01.747501-06	2026-07-07 13:28:01.747501-06	t	\N	\N
69	Sergio Gonzalez Corral	calidad@calzasider.com	+52 33 3812 0198	\N	19	2026-07-07 13:28:01.756465-06	2026-07-07 13:28:01.756465-06	t	\N	\N
73	veronica.guzman@claseazul.com>	veronica.guzman@claseazul.com	\N	\N	20	2026-07-07 13:28:01.766283-06	2026-07-07 13:28:01.766283-06	t	\N	\N
75	Jazmín Flores Hernandez	jazmin.flores@cmiinmx.com.mx	+52 722 341 1382	\N	21	2026-07-07 13:28:01.772403-06	2026-07-07 13:28:01.772403-06	t	\N	\N
77	Rodrigo Rodriguez	\N	\N	\N	22	2026-07-07 13:28:01.778983-06	2026-07-07 13:28:01.778983-06	t	\N	\N
78	Araceli Zuñiga	analistadecalidad@cohmedic.com	+52 33 3188 7807	\N	23	2026-07-07 13:28:01.782072-06	2026-07-07 13:28:01.782072-06	t	\N	\N
83	Ing. Carlos Cantellano	ccantellano@gonac.com.mx	\N	\N	24	2026-07-07 13:28:01.794742-06	2026-07-07 13:28:01.794742-06	t	\N	\N
84	Maritza Torres	atencion_clientesgdl@comintec.com.mx	+52 33 2338 1031	\N	25	2026-07-07 13:28:01.798304-06	2026-07-07 13:28:01.798304-06	t	\N	\N
87	Jesus Cortes	\N	+52 618 301 5011	\N	26	2026-07-07 13:28:01.807398-06	2026-07-07 13:28:01.807398-06	t	\N	\N
96	IVAN CASTILLO	\N	+52 33 2543 3475	\N	27	2026-07-07 13:28:01.831815-06	2026-07-07 13:28:01.831815-06	t	\N	\N
97	Jorge Gallo	direccion@basculasgallo.com.mx	+52 33 1411 4557	\N	28	2026-07-07 13:28:01.834456-06	2026-07-07 13:28:01.834456-06	t	\N	\N
98	Antonio Villalobos	\N	+52 33 3700 3141	\N	29	2026-07-07 13:28:01.836892-06	2026-07-07 13:28:01.836892-06	t	\N	\N
106	Luis Garibay	lgaribay@eurostern.com.mx	+52 33 2725 7188	\N	30	2026-07-07 13:28:01.856444-06	2026-07-07 13:28:01.856444-06	t	\N	\N
108	LILIANA MARISCAL	liliana.mariscal@fanosa.com	+52 33 1894 8238	\N	31	2026-07-07 13:28:01.862716-06	2026-07-07 13:28:01.862716-06	t	\N	\N
113	ARTURO GONZALEZ MARIN	arturo.gonzalez@fpi-isa.com	+52 229 227 7952	\N	32	2026-07-07 13:28:01.87619-06	2026-07-07 13:28:01.87619-06	t	\N	\N
122	Luis Canales	\N	\N	\N	33	2026-07-07 13:28:01.898032-06	2026-07-07 13:28:01.898032-06	t	\N	\N
125	Alberto Aldrete Armenta	\N	+52 33 3141 7010	\N	34	2026-07-07 13:28:01.906356-06	2026-07-07 13:28:01.906356-06	t	\N	\N
132	Luis Arcadia	luis.arcadia@gdl.fii-na.com	+52 33 3955 9033	\N	35	2026-07-07 13:28:01.923572-06	2026-07-07 13:28:01.923572-06	t	\N	\N
134	Francisco Javier Ordaz Higareda	\N	+52 341 117 6267	\N	36	2026-07-07 13:28:01.928866-06	2026-07-07 13:28:01.928866-06	t	\N	\N
136	Roberto Bernal	rbernal@sugarfoodsdemexico.com	+52 772 261 3513	\N	37	2026-07-07 13:28:01.933947-06	2026-07-07 13:28:01.933947-06	t	\N	\N
142	Gloria Leon	\N	+52 33 1601 2194	\N	38	2026-07-07 13:28:01.947065-06	2026-07-07 13:28:01.947065-06	t	\N	\N
143	Xitlali	asistenteoperativo@grupoalferelectric.com	+52 33 3465 7033	\N	39	2026-07-07 13:28:01.949001-06	2026-07-07 13:28:01.949001-06	t	\N	\N
146	Yeni Gonzalez Martinez	yeni.gonzalez@gcollado.com	+52 33 3161 6254	\N	40	2026-07-07 13:28:01.955943-06	2026-07-07 13:28:01.955943-06	t	\N	\N
147	Daniela Maria Moreno Cardona	daniela.moreno@grupoexcala.com	+57 313 7671627	\N	41	2026-07-07 13:28:01.958443-06	2026-07-07 13:28:01.958443-06	t	\N	\N
160	Erika Padilla	Erika_Padilla@hdm.honda.com	\N	\N	42	2026-07-07 13:28:01.986045-06	2026-07-07 13:28:01.986045-06	t	\N	\N
162	MAF. Alejandra CervantesSantiago	jefaturadelaboratorio@hsmgdl.com	\N	\N	43	2026-07-07 13:28:01.990749-06	2026-07-07 13:28:01.990749-06	t	\N	\N
167	MARICELA RIVERA CALVILLO	maricela_rivera@ider.mx	+52 33 3836 0600	\N	44	2026-07-07 13:28:02.000877-06	2026-07-07 13:28:02.000877-06	t	\N	\N
168	Marvin Paredes	\N	\N	\N	45	2026-07-07 13:28:02.003147-06	2026-07-07 13:28:02.003147-06	t	\N	\N
169	Jesus Granados	\N	+52 33 1604 1833	\N	46	2026-07-07 13:28:02.005604-06	2026-07-07 13:28:02.005604-06	t	\N	\N
171	Dionisio Casillas	administracion@industrialdci.com	+52 33 1133 9862	\N	47	2026-07-07 13:28:02.009665-06	2026-07-07 13:28:02.009665-06	t	\N	\N
173	gabriel.carraman@ie3.mx	gabriel.carraman@ie3.mx	+52 33 1670 0424	\N	48	2026-07-07 13:28:02.013415-06	2026-07-07 13:28:02.013415-06	t	\N	\N
174	ESMERALDA LOPEZ	esmeralda.lopez@fii-na.com	+52 33 3613 4881	\N	49	2026-07-07 13:28:02.015577-06	2026-07-07 13:28:02.015577-06	t	\N	\N
176	Ing. Maite Morales	biomedico@innovarecirugiaplastica.com	\N	\N	50	2026-07-07 13:28:02.019949-06	2026-07-07 13:28:02.019949-06	t	\N	\N
181	Leonardo Garcia	\N	+52 33 1095 3643	\N	51	2026-07-07 13:28:02.02963-06	2026-07-07 13:28:02.02963-06	t	\N	\N
186	Jennifer Rosales	auxadmin@itesvia.com.mx	+52 33 3254 7014	\N	52	2026-07-07 13:28:02.040703-06	2026-07-07 13:28:02.040703-06	t	\N	\N
187	Alejandro Gama	\N	\N	\N	53	2026-07-07 13:28:02.043161-06	2026-07-07 13:28:02.043161-06	t	\N	\N
190	juan.pablo.mendoza.roman@gmail.com	\N	\N	\N	54	2026-07-07 13:28:02.050357-06	2026-07-07 13:28:02.050357-06	t	\N	\N
191	Jimena	\N	+52	\N	55	2026-07-07 13:28:02.052144-06	2026-07-07 13:28:02.052144-06	t	\N	\N
197	Sergio Jerónimo	sergio210295@gmail.com	+52 56 2005 0936	\N	56	2026-07-07 13:28:02.062904-06	2026-07-07 13:28:02.062904-06	t	\N	\N
201	Fátima Carbajal	pinturasacuariodmzo@hotmail.com	+52 314 872 5026	\N	57	2026-07-07 13:28:02.070894-06	2026-07-07 13:28:02.070894-06	t	\N	\N
209	Ivan Farias	eduardo_ramirez@leco.com	+52 33 2488 0705	\N	58	2026-07-07 13:28:02.086115-06	2026-07-07 13:28:02.086115-06	t	\N	\N
210	Yessica Ramirez	\N	+52 462 191 5019	\N	59	2026-07-07 13:28:02.088568-06	2026-07-07 13:28:02.088568-06	t	\N	\N
218	Juan Manuel Gallegos García	calidad@mcprocesos.com	+52 33 3693 6446	\N	60	2026-07-07 13:28:02.10341-06	2026-07-07 13:28:02.10341-06	t	\N	\N
226	Oscar Lescutia	\N	+52 33 3474 0685	\N	61	2026-07-07 13:28:02.119028-06	2026-07-07 13:28:02.119028-06	t	\N	\N
227	Teresa Moreno	compras@grupomad.mx	+52 33 1423 7359	\N	62	2026-07-07 13:28:02.121653-06	2026-07-07 13:28:02.121653-06	t	\N	\N
232	Andy Pelayo	administracion@medeticorp.com	+52 33 3129 8141	\N	63	2026-07-07 13:28:02.130902-06	2026-07-07 13:28:02.130902-06	t	\N	\N
233	ING. Angélica Reyes Ayala	especialista1@medikalmuneris.com	+52 33 1293 6702	\N	64	2026-07-07 13:28:02.133598-06	2026-07-07 13:28:02.133598-06	t	\N	\N
235	Julian Pacheco	compras@bigvento.com	+52 33 3617 6462	\N	65	2026-07-07 13:28:02.138304-06	2026-07-07 13:28:02.138304-06	t	\N	\N
236	Misael Rojas	misael@metrologiazelkova.com	\N	\N	66	2026-07-07 13:28:02.140683-06	2026-07-07 13:28:02.140683-06	t	\N	\N
245	Claudia Medina	\N	+52 33 3821 0651	\N	67	2026-07-07 13:28:02.159907-06	2026-07-07 13:28:02.159907-06	t	\N	\N
269	ANTONIO BRISEÑO	\N	+52 33 3183 7229	\N	71	2026-07-07 13:28:02.210993-06	2026-07-07 13:28:02.210993-06	t	\N	\N
297	Ing. Suarez	gerencia@maderasguadalupana.com	+52 33 1429 8240	\N	75	2026-07-07 13:28:02.26339-06	2026-07-07 13:28:02.26339-06	t	\N	\N
345	Vanessa Castellanos	vanessa.castellanos@uwicorp.com	+52 378 186 8564	\N	86	2026-07-07 13:28:02.400014-06	2026-07-07 13:28:02.400014-06	t	\N	\N
251	Jackie Pinedo	gerenteservicioar@naosavw.com	+52 33 3502 4864	\N	68	2026-07-07 13:28:02.173165-06	2026-07-07 13:28:02.173165-06	t	\N	\N
263	Israel Jimenez	\N	+52 33 3468 4767	\N	70	2026-07-07 13:28:02.199214-06	2026-07-07 13:28:02.199214-06	t	\N	\N
295	SAMUEL NAVARRO	ngs@saverglass.com	+52 33 3905 3661	\N	74	2026-07-07 13:28:02.259786-06	2026-07-07 13:28:02.259786-06	t	\N	\N
343	Ivonne	ventas@suspensionesensa.com	+52 33 3619 8679	\N	85	2026-07-07 13:28:02.396257-06	2026-07-07 13:28:02.396257-06	t	\N	\N
351	Guatavo Vargas	gustavo.vargas@vwdelcentro.com.mx	+52 449 182 0510	\N	87	2026-07-07 13:28:02.41176-06	2026-07-07 13:28:02.41176-06	t	\N	\N
355	Sotelo Bryan	sotelob777@gmail.com	+52 33 1990 0045	\N	89	2026-07-07 13:28:02.418794-06	2026-07-07 13:28:02.418794-06	t	\N	\N
359	BRIAN	produccion@zurichtec.com.mx	+52 378 118 7914	\N	91	2026-07-07 13:28:02.426648-06	2026-07-07 13:28:02.426648-06	t	\N	\N
363	Minerva Ramirez	minervadiprocat@gmail.com	+52 33 2507 4880	\N	93	2026-07-07 13:28:02.435347-06	2026-07-07 13:28:02.435347-06	t	\N	\N
262	Pedro Aguilar	comprador4@ortopedisalud.com	+52 33 2071 0054	\N	69	2026-07-07 13:28:02.197102-06	2026-07-07 13:28:02.197102-06	t	\N	\N
282	Salvador Izquierdo Coria	seguridad.industrial@rycandy.com	+52 33 3836 3700	\N	72	2026-07-07 13:28:02.235309-06	2026-07-07 13:28:02.235309-06	t	\N	\N
286	Elizabeth Rojas	eelizabeth@rogersfoam.com	\N	\N	73	2026-07-07 13:28:02.243478-06	2026-07-07 13:28:02.243478-06	t	\N	\N
298	Hugo Bonilla	hugo@sialico.com	\N	\N	76	2026-07-07 13:28:02.265363-06	2026-07-07 13:28:02.265363-06	t	\N	\N
314	Martín Pastor	calidad@sazonnatural.com	+52 33 1199 4765	\N	80	2026-07-07 13:28:02.334618-06	2026-07-07 13:28:02.334618-06	t	\N	\N
322	Montserrat Pozos Ponce	compras@sherexmx.com	+52 442 196 8075	\N	81	2026-07-07 13:28:02.352786-06	2026-07-07 13:28:02.352786-06	t	\N	\N
326	Francisco Mora	francisco.moraramirez@hotmail.com	+52 33 1948 3918	\N	82	2026-07-07 13:28:02.360743-06	2026-07-07 13:28:02.360743-06	t	\N	\N
342	María Jose Reyes	maria.reyes@f-tam.com	+52 33 3796 0510	\N	84	2026-07-07 13:28:02.394229-06	2026-07-07 13:28:02.394229-06	t	\N	\N
354	Teresita Cabrera	teresita.cabrera@wasion.com	+52 472 690 8060	\N	88	2026-07-07 13:28:02.416929-06	2026-07-07 13:28:02.416929-06	t	\N	\N
304	Juan Josue	\N	+52 33 1604 9402	\N	77	2026-07-07 13:28:02.312592-06	2026-07-07 13:28:02.312592-06	t	\N	\N
308	Diego Rodríguez Peraza	df.rodriguez@saleiko.com	+52 33 3033 7926	\N	78	2026-07-07 13:28:02.321773-06	2026-07-07 13:28:02.321773-06	t	\N	\N
312	Magi	\N	+52 33 1092 1243	\N	79	2026-07-07 13:28:02.329954-06	2026-07-07 13:28:02.329954-06	t	\N	\N
332	CLARA MARROQUIN	almacenjcompany@gmail.com	\N	\N	83	2026-07-07 13:28:02.372173-06	2026-07-07 13:28:02.372173-06	t	\N	\N
356	Alberto Lopez	servicioyaliercp@hotmail.com	+52 33 3723 1524	\N	90	2026-07-07 13:28:02.4211-06	2026-07-07 13:28:02.4211-06	t	\N	\N
360	Francisco Hernandez	calidad_zarkruse@zar-kruse.com	+52 729 531 7213	\N	92	2026-07-07 13:28:02.428947-06	2026-07-07 13:28:02.428947-06	t	\N	\N
21	Luis Varela	luis.varela@adler-la.com	+52 33 3033 7809	\N	94	2026-07-07 14:36:19.733733-06	2026-07-07 14:36:19.733733-06	t	\N	\N
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.clients (legal_name, commercial_name, rfc, email, phone, tax_regime, payment_terms, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, cfdi_use, street, exterior_number, interior_number, neighborhood, city, state, postal_code, country, fiscal_postal_code, tax_constancy_filename, tax_constancy_path, tax_constancy_uploaded_at, client_type, curp, first_name, first_last_name, second_last_name, street_type, locality, municipality) FROM stdin;
Adler Pharma, S. de R.L. de C.V.	Adler Pharma, S. de R.L. de C.V.	XAXX010101000	luis.varela@adler-la.com	+52 33 3033 7809	General de Ley de Personas Morales	\N	\N	21	2026-07-07 13:28:01.599883-06	2026-07-07 16:36:32.188743-06	f	2026-07-07 16:36:32.19228-06	\N	\N	Miguel Alemán No. 6926	\N	\N	\N	Zapopan	Jalisco	45236	Mexico	45236	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
ADM Packaging Services S de RL de CV	ADM Packaging Services S de RL de CV	XAXX010101000	Miriam@admpackaging.com	+52 353 123 8640	General de Ley de Personas Morales	\N	\N	3	2026-07-07 13:28:01.526197-06	2026-07-07 16:36:32.204528-06	f	2026-07-07 16:36:32.206209-06	\N	\N	Puerto Ensenada 1075, Col. Miramar	\N	\N	\N	Zapopan	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Aeroplasa de Occidente, S.A. de C.V.	Aeroplasa de Occidente, S.A. de C.V.	XAXX010101000	gteservicio@aeroplasadeoccidente.com	+52 311 270 3229	General de Ley de Personas Morales	\N	\N	22	2026-07-07 13:28:01.604491-06	2026-07-07 16:36:32.217646-06	f	2026-07-07 16:36:32.219916-06	\N	\N	Av. Insurgentes Poniente S/N	\N	\N	\N	Tepic	Nayarit	63000	Mexico	63000	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tepic
AGRO FRESAM	AGRO FRESAM	XAXX010101000	gestiondelacalidad@agrofresam.com.mx	+1 800-890-7825	General de Ley de Personas Morales	\N	\N	4	2026-07-07 13:28:01.532171-06	2026-07-07 16:36:32.229975-06	f	2026-07-07 16:36:32.232151-06	\N	\N	BACHILLERES 39 EJIDAL	\N	\N	\N	JACONA	Michoacán	59893	Mexico	59893	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	JACONA
Agrovet Market México	Agrovet Market México	\N	aurora.lopez@agrovetmarket.com.mx	+52 33 3682 2036	General de Ley de Personas Morales	\N	\N	23	2026-07-07 13:28:01.608484-06	2026-07-07 16:36:32.242257-06	f	2026-07-07 16:36:32.243725-06	\N	\N	Calle La Brida #247. Interior 1 Col. López Cotilla	\N	\N	\N	Tlaquepaque	Jalisco	45615	Mexico	45615	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
AGUA BLUE ROCK	AGUA BLUE ROCK	\N	jorgerossains@aguabluerock.com	\N	General de Ley de Personas Morales	\N	\N	5	2026-07-07 13:28:01.538702-06	2026-07-07 16:36:32.254591-06	f	2026-07-07 16:36:32.256466-06	\N	\N	\N	\N	\N	\N	Guadalajara	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Alberto Evangelista Placencia	Alberto Evangelista Placencia	\N	aevangelmx@gmail.com	+52 33 3105 8858	Sin obligaciones fiscales	\N	\N	24	2026-07-07 13:28:01.612334-06	2026-07-07 16:36:32.266543-06	f	2026-07-07 16:36:32.268908-06	\N	\N	Privada Zacatecas #2605-4	\N	\N	\N	santiago Monoxpan Cholula	\N	72775	Mexico	72775	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	santiago Monoxpan Cholula
ALLIANCER S.A. DE C.V.	ALLIANCER S.A. DE C.V.	\N	\N	+52 55 5863 3801	General de Ley de Personas Morales	\N	\N	6	2026-07-07 13:28:01.545399-06	2026-07-07 16:36:32.279469-06	f	2026-07-07 16:36:32.281241-06	\N	\N	CALLE ADALBERTO TEJADA 39	\N	\N	\N	México	Ciudad de México	13210	Mexico	13210	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	México
Allison Rebeca	Allison Rebeca	\N	atencion_clientesgdl7@comintec.com.mx	\N	\N	\N	\N	25	2026-07-07 13:28:01.617571-06	2026-07-07 16:36:32.290686-06	f	2026-07-07 16:36:32.292556-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Ambiderm, S.A. de C.V.	Ambiderm, S.A. de C.V.	\N	metrologo@ambiderm.com.mx	+52 33 3656 6557	General de Ley de Personas Morales	\N	\N	26	2026-07-07 13:28:01.621776-06	2026-07-07 16:36:32.30418-06	f	2026-07-07 16:36:32.305827-06	\N	\N	Carr. a Bosques de San Isidro No. 1136	\N	\N	\N	Zapopan	Jalisco	45133	Mexico	45133	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
American Industries	American Industries	\N	AlmaF@wanpy.com.cn	+52 55 7461 5101	General de Ley de Personas Morales	\N	\N	27	2026-07-07 13:28:01.624783-06	2026-07-07 16:36:32.315052-06	f	2026-07-07 16:36:32.317234-06	\N	\N	Blvd. Puerta de Hierro No. 5200 Int. 7 Puerta de Hierro Business Center	\N	\N	\N	Zapopan	Jalisco	45116	Mexico	45116	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
AMMED	AMMED	\N	coordinacion.servicio@ammed.com.mx	+52 33 3663 1249	General de Ley de Personas Morales	\N	\N	7	2026-07-07 13:28:01.549201-06	2026-07-07 16:36:32.328115-06	f	2026-07-07 16:36:32.329922-06	\N	\N	España #1591, Moderna	\N	\N	\N	Guadalajara	Jalisco	44190	Mexico	44190	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
APC Procesadora Anáhuac, S.A. de C.V.	APC Procesadora Anáhuac, S.A. de C.V.	\N	inspeccion@apcanodos.com	\N	General de Ley de Personas Morales	\N	\N	8	2026-07-07 13:28:01.553108-06	2026-07-07 16:36:32.339356-06	f	2026-07-07 16:36:32.34078-06	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
APX MS	APX MS	\N	fredy.rico@apxmultiservicios.com	+52 442 669 9152	General de Ley de Personas Morales	\N	\N	9	2026-07-07 13:28:01.557145-06	2026-07-07 16:36:32.350041-06	f	2026-07-07 16:36:32.352034-06	\N	\N	VALLE DE OROZ 1328, COL. MIRAVALLE	\N	\N	\N	CIUDAD OBREGON	Sonora	85090	Mexico	85090	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CIUDAD OBREGON
Asesores en equipos de proteccion industrial sire	Asesores en equipos de proteccion industrial sire	\N	jonathancancino@asesoressire.com.mx	+52 33 3019 4490	General de Ley de Personas Morales	\N	\N	28	2026-07-07 13:28:01.627437-06	2026-07-07 16:36:32.376051-06	f	2026-07-07 16:36:32.377718-06	\N	\N	isla Madagascar 3075	\N	\N	\N	Guadalajara	Jalisco	44950	Mexico	44950	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Asiip	Asiip	\N	ingvalidacion01@asiip.com.mx	+52 55 2607 9060	General de Ley de Personas Morales	\N	\N	29	2026-07-07 13:28:01.630542-06	2026-07-07 16:36:32.399727-06	f	2026-07-07 16:36:32.402027-06	\N	\N	Manuel M. Ponce 322 Oficina 201	\N	\N	\N	Alvaro Obregon	Ciudad de México	01020	Mexico	01020	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Alvaro Obregon
ASOCIACION MEXICANA DE INSPECCION DE INFORMACION COMERCIAL AMIIC	ASOCIACION MEXICANA DE INSPECCION DE INFORMACION COMERCIAL AMIIC	\N	e.mendoza@amiic.org	+52 777 277 6977	General de Ley de Personas Morales	\N	\N	12	2026-07-07 13:28:01.567517-06	2026-07-07 16:36:32.412069-06	f	2026-07-07 16:36:32.413674-06	\N	\N	CITLALLI 19, INT 1.	\N	\N	\N	HUITZILAC	Morelos	62515	Mexico	62515	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	HUITZILAC
ASPHALT PAVEMENT & CONSTRUCTION LABORATORIES	ASPHALT PAVEMENT & CONSTRUCTION LABORATORIES	\N	hrodriguez@mulsa.com.mx	+52 392 930 3510	General de Ley de Personas Morales	\N	\N	13	2026-07-07 13:28:01.571153-06	2026-07-07 16:36:32.422102-06	f	2026-07-07 16:36:32.424016-06	\N	\N	AV. ACUEDUCTO ORIENTE	\N	\N	\N	IXTLAHUACAN DE LOS MEMBRILLOS	Jalisco	45860	Mexico	45860	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	IXTLAHUACAN DE LOS MEMBRILLOS
Atisa Mx	Atisa Mx	\N	yadira.silva@atisamx.com	\N	\N	\N	\N	30	2026-07-07 13:28:01.634474-06	2026-07-07 16:36:32.433741-06	f	2026-07-07 16:36:32.435512-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
ATS	ATS	\N	marmaldo@advancedtech.com	+52 461 202 1350 ext. 50260	General de Ley de Personas Morales	\N	\N	14	2026-07-07 13:28:01.575428-06	2026-07-07 16:36:32.44419-06	f	2026-07-07 16:36:32.446057-06	\N	\N	AVENIDA REYNOSA 3202 , COL. GUERRERO	\N	\N	\N	NUEVO LAREDO	Tamaulipas	64920	Mexico	64920	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	NUEVO LAREDO
ATS, Josed De Jesus Valdez Roman	ATS, Josed De Jesus Valdez Roman	\N	jvaldez@advancedtech.com	\N	\N	\N	\N	15	2026-07-07 13:28:01.578184-06	2026-07-07 16:36:32.4551-06	f	2026-07-07 16:36:32.456487-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
AUDI LOPEZ MATEOS	AUDI LOPEZ MATEOS	\N	haltamirano@audilm.mx	+52 33 3050 8888	General de Ley de Personas Morales	\N	\N	16	2026-07-07 13:28:01.581637-06	2026-07-07 16:36:32.49153-06	f	2026-07-07 16:36:32.493034-06	\N	\N	NIÑOS HEROES 716, JARDINES DE LOS ARCOS	\N	\N	\N	GUADALAJARA	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
AUTOCAMIONES DE MEXICO	AUTOCAMIONES DE MEXICO	\N	a.atondo@autocamiones.mx	+52 697 109 8345	General de Ley de Personas Morales	\N	\N	17	2026-07-07 13:28:01.585544-06	2026-07-07 16:36:32.504342-06	f	2026-07-07 16:36:32.506611-06	\N	\N	Fray marcos de niza 3486 colonia san rafael	\N	\N	\N	Culiacan	Sinaloa	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Culiacan
AUTOMOTORES FLOVA	AUTOMOTORES FLOVA	\N	gerenteservicio@autosflova.com	+52 322 221 1200	General de Ley de Personas Morales	\N	\N	18	2026-07-07 13:28:01.589839-06	2026-07-07 16:36:32.517891-06	f	2026-07-07 16:36:32.520109-06	\N	\N	BOULEVARD PUERTA DE HIERRO 5200- 14	\N	\N	\N	ZAPOPAN	Jalisco	45116	Mexico	45116	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
AUTONOVA	AUTONOVA	\N	leonel.casillas@autonova.com.mx	+52 33 3619 3672	General de Ley de Personas Morales	\N	\N	19	2026-07-07 13:28:01.592995-06	2026-07-07 16:36:32.543311-06	f	2026-07-07 16:36:32.544922-06	\N	\N	AV. 16 DE SEPTIEMBRE #1066, MODERNA GUADALAJARA	\N	\N	\N	GUADALAJARA	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
AVFRA INDUSTRIES	AVFRA INDUSTRIES	\N	areli777@hotmail.com	+52 33 1050 1765	General de Ley de Personas Morales	\N	\N	10	2026-07-07 13:28:01.560347-06	2026-07-07 16:36:32.555781-06	f	2026-07-07 16:36:32.557545-06	\N	\N	ATARDECER 160 INT. 185	\N	\N	\N	TLAQUEPAQUE	Jalisco	45602	Mexico	45602	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAQUEPAQUE
AVISAIL FLORES LUNA	AVISAIL FLORES LUNA	\N	ventas.calinsto@gmail.com	\N	General de Ley de Personas Morales	\N	\N	20	2026-07-07 13:28:01.5957-06	2026-07-07 16:36:32.56908-06	f	2026-07-07 16:36:32.571616-06	\N	\N	CALLE BRILLANTE #1576, COL. MARIANO OTERO	\N	\N	\N	ZAPOPAN	Jalisco	45067	Mexico	45067	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
Betone	Betone	\N	compras1@betone.net	+52 33 3682 1320	General de Ley de Personas Morales	\N	\N	39	2026-07-07 13:28:01.6669-06	2026-07-07 16:36:32.595723-06	f	2026-07-07 16:36:32.597853-06	\N	\N	Periferico poniente $7100, Ciudad Granja	\N	\N	\N	zapopan	Jalisco	45010	Mexico	45010	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	zapopan
CAFISON	CAFISON	\N	auxiliar.compras@cafison.com	+52 33 1593 6116	General de Ley de Personas Morales	\N	\N	43	2026-07-07 13:28:01.680802-06	2026-07-07 16:36:32.695393-06	f	2026-07-07 16:36:32.696831-06	\N	\N	Av Vallarta $4951, Prados.	\N	\N	\N	Zapopan	Jalisco	45020	Mexico	45020	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Calkins Burke and Zannie de México, S.A. de C.V.	Calkins Burke and Zannie de México, S.A. de C.V.	\N	umplimiento@mexcorina.com	+52 33 3283 4500	General de Ley de Personas Morales	\N	\N	67	2026-07-07 13:28:01.751015-06	2026-07-07 16:36:32.733581-06	f	2026-07-07 16:36:32.735835-06	\N	\N	Priv. Ixtepete No.12	\N	\N	\N	Zapopan	Jalisco	45071	Mexico	45071	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Carbotecnia, S.A. de C.V.	Carbotecnia, S.A. de C.V.	\N	laboratorio@carbotecnia.com.mx	\N	General de Ley de Personas Morales	\N	\N	71	2026-07-07 13:28:01.761594-06	2026-07-07 16:36:36.41021-06	f	2026-07-07 16:36:36.412835-06	\N	\N	Calle B 2105 Interior A, Col. del Tigre	\N	\N	\N	Zapopan	Jalisco	45134	Mexico	45134	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
CENTRO DE DESARROLLO EN INSTRUMENTACION Y CAPACITACION	CENTRO DE DESARROLLO EN INSTRUMENTACION Y CAPACITACION	\N	ventas@cedica.mx	\N	General de Ley de Personas Morales	\N	\N	47	2026-07-07 13:28:01.694342-06	2026-07-07 16:36:36.490623-06	f	2026-07-07 16:36:36.492219-06	\N	\N	Niños Heroes 264 Lomas del Camichin	\N	\N	\N	TONALA	Jalisco	45417	Mexico	45417	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TONALA
Centro de Metrología Ingeniería e Innovación	Centro de Metrología Ingeniería e Innovación	\N	jazmin.flores@cmiinmx.com.mx	+52 722 341 1382	\N	\N	\N	75	2026-07-07 13:28:01.772403-06	2026-07-07 16:36:36.502298-06	f	2026-07-07 16:36:36.504083-06	\N	\N	Edo. México, Toluca	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
CHUPALETAS S.A. DE C.V.	CHUPALETAS S.A. DE C.V.	\N	auxcompras.ch@delarosa.com.mx	+52 33 3823 0808	General de Ley de Personas Morales	\N	\N	51	2026-07-07 13:28:01.706478-06	2026-07-07 16:36:36.554116-06	f	2026-07-07 16:36:36.555503-06	\N	\N	CARRETERA CAMINO A LA CALERILLA 1550-C	\N	\N	\N	Tlaquepaque	Jalisco	45602	Mexico	45602	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
Collins División Veterinaria	Collins División Veterinaria	\N	supervisor.produccion@collinsdv.com.mx	+52 33 3811 1464	General de Ley de Personas Morales	\N	\N	79	2026-07-07 13:28:01.785406-06	2026-07-07 16:36:36.595534-06	f	2026-07-07 16:36:36.597278-06	\N	\N	Calle Rotonda 12	\N	\N	\N	Guadalajara	Jalisco	44440	Mexico	44440	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Comercializadora Gonac, S.A. de C.V.	Comercializadora Gonac, S.A. de C.V.	\N	ccantellano@gonac.com.mx	\N	General de Ley de Personas Morales	\N	\N	83	2026-07-07 13:28:01.794742-06	2026-07-07 16:36:36.637243-06	f	2026-07-07 16:36:36.638679-06	\N	\N	Jalisco Vialidad Beijing N° 200. Parque Industrial Centro Logístico Jalisco  ...	\N	\N	\N	Acatlan de juarez	Jalisco	45713	Mexico	45713	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Acatlan de juarez
CONCRETOS LANZADOS CONSTRUCCIONES	CONCRETOS LANZADOS CONSTRUCCIONES	\N	miriamconchas.clc@gmail.com	+52 33 1309 6909	General de Ley de Personas Morales	\N	\N	55	2026-07-07 13:28:01.716951-06	2026-07-07 16:36:36.691574-06	f	2026-07-07 16:36:36.693292-06	\N	\N	AVENIDA DE LAS GONDOLAS 290, VALLE DEL ALAMO	\N	\N	\N	GUADALAJARA	Jalisco	44440	Mexico	44440	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Construcciones e Ingeniería Especializada del Norte, S.A. de C.V.	Construcciones e Ingeniería Especializada del Norte, S.A. de C.V.	\N	\N	+52 618 301 5011	General de Ley de Personas Morales	\N	\N	87	2026-07-07 13:28:01.807398-06	2026-07-07 16:36:36.746299-06	f	2026-07-07 16:36:36.747925-06	\N	\N	Felipe Mendia 304, Industrial Ladrillera	\N	\N	\N	Durango	Durango	34289	Mexico	34289	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Durango
CONSULTEC SRV	CONSULTEC SRV	\N	joel.ramirez@consultecsrv.com	+52 33 1013 1344	General de Ley de Personas Morales	\N	\N	59	2026-07-07 13:28:01.72743-06	2026-07-07 16:36:36.762136-06	f	2026-07-07 16:36:36.764492-06	\N	\N	Prolongación colón #88, int: 4	\N	\N	\N	San Pedro Tlauqepaque	Jalisco	45600	Mexico	45600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlauqepaque
CRAFT AVÍA CENTER	CRAFT AVÍA CENTER	\N	luisa.salazar@craftaviacenter.com	+52 33 2101 1060	General de Ley de Personas Morales	\N	\N	63	2026-07-07 13:28:01.738554-06	2026-07-07 16:36:36.819531-06	f	2026-07-07 16:36:36.820988-06	\N	\N	TORRE PANAMÁ ACUEDUCTO, AV REAL DE ACUEDUCTO #335	\N	\N	\N	Zapopan	Jalisco	45116	Mexico	45116	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Eagle Ice Fruit, S.A. de C.V.	Eagle Ice Fruit, S.A. de C.V.	\N	jose.alejos@eagleicef.com.mx	+52 351 167 3131	General de Ley de Personas Morales	\N	\N	99	2026-07-07 13:28:01.840056-06	2026-07-07 16:36:36.918626-06	f	2026-07-07 16:36:36.92107-06	\N	\N	Constitucion Norte No. 408 B	\N	\N	\N	Jacona de Plancarte	Michoacán	59800	Mexico	59800	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Jacona de Plancarte
EATON BUSSMANN S DE RL DE CV	EATON BUSSMANN S DE RL DE CV	\N	alberto.espinosa@vallenproveedora.com.mx	+52 477 854 8248	General de Ley de Personas Morales	\N	\N	95	2026-07-07 13:28:01.829715-06	2026-07-07 16:36:36.933795-06	f	2026-07-07 16:36:36.936066-06	\N	\N	AV. LA ESTACADA 451. PARQUE INDUSTRIAL	\N	\N	\N	QUERETARO	Querétaro	76220	Mexico	76220	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	QUERETARO
Elevadores Fergar, S.A. de C.V.	Elevadores Fergar, S.A. de C.V.	\N	Jgaribay@grupoibero.com.mx	+52 33 1828 4071	General de Ley de Personas Morales	\N	\N	103	2026-07-07 13:28:01.84886-06	2026-07-07 16:36:40.238341-06	f	2026-07-07 16:36:40.24198-06	\N	\N	Acueducto No. 4851 Piso 11	\N	\N	\N	Guadalajara	Jalisco	45116	Mexico	45116	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Exportaciones Zepeda	Exportaciones Zepeda	\N	exportacioneszepeda@gmail.com	+52 317 121 0714	\N	\N	\N	107	2026-07-07 13:28:01.859948-06	2026-07-07 16:36:40.304922-06	f	2026-07-07 16:36:40.306339-06	\N	\N	prol. Guadalupe Victoria 3064	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Fabrica de Cajas y Empaques La Providencia	Fabrica de Cajas y Empaques La Providencia	\N	lizzet7111981@hotmail.com	+52 33 1412 6769	\N	\N	\N	123	2026-07-07 13:28:01.900984-06	2026-07-07 16:36:40.315428-06	f	2026-07-07 16:36:40.317084-06	\N	\N	Crisóforo Canseco 173	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
FERMIN ZUÑIGA DIAZ	FERMIN ZUÑIGA DIAZ	\N	\N	+52 386 103 6594	General de Ley de Personas Morales	\N	\N	111	2026-07-07 13:28:01.87143-06	2026-07-07 16:36:40.378706-06	f	2026-07-07 16:36:40.380391-06	\N	\N	Juarez 300, Etzatlan Centro	\N	\N	\N	Etzatlan	Jalisco	46500	Mexico	46500	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Etzatlan
FISCALIA GENERAL COLIMA	FISCALIA GENERAL COLIMA	\N	anahi.medina@fgr.org.mx	\N	General de Ley de Personas Morales	\N	\N	115	2026-07-07 13:28:01.881452-06	2026-07-07 16:36:40.438348-06	f	2026-07-07 16:36:40.439797-06	\N	\N	LIBRAMIENTO MARCELINO GARCÍA BARRAGAN B/N KM 3,350	\N	\N	\N	COLIMA	Colima	28048	Mexico	28048	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	COLIMA
Flosol Eulogio Parra	Flosol Eulogio Parra	\N	\N	+52 33 1845 8048	\N	\N	\N	127	2026-07-07 13:28:01.911102-06	2026-07-07 16:36:40.475926-06	f	2026-07-07 16:36:40.477711-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Food Microbiology Laboratories, Nancy Ramirez	Food Microbiology Laboratories, Nancy Ramirez	\N	nancy.ramirez@foodmicrolab.com	\N	General de Ley de Personas Morales	\N	\N	131	2026-07-07 13:28:01.92103-06	2026-07-07 16:36:40.542338-06	f	2026-07-07 16:36:40.54372-06	\N	\N	Fundicion #2144 col. Parque Industrial El Alamo	\N	\N	\N	Guadalajara	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
FR TERMINALES	FR TERMINALES	\N	comprasate@frterminales.com	+52 376 737 1996	General de Ley de Personas Morales	\N	\N	119	2026-07-07 13:28:01.891443-06	2026-07-07 16:36:40.564697-06	f	2026-07-07 16:36:40.56691-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
GAMI INGENIERIA E INSTALACIONES	GAMI INGENIERIA E INSTALACIONES	\N	mariana.urrecha@grupoindi.com	+52 55 4133 5830	General de Ley de Personas Morales	\N	\N	135	2026-07-07 13:28:01.931464-06	2026-07-07 16:36:40.631532-06	f	2026-07-07 16:36:40.63384-06	\N	\N	Zapotecas 17, Santa Cruz Acatlán	\N	\N	\N	Naucalpan de Juárez	México	53150	Mexico	53150	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Naucalpan de Juárez
Grupo Alferelectric, S.A. de C.V.	Grupo Alferelectric, S.A. de C.V.	\N	asistenteoperativo@grupoalferelectric.com	+52 33 3465 7033	General de Ley de Personas Morales	\N	\N	143	2026-07-07 13:28:01.949001-06	2026-07-07 16:36:40.734985-06	f	2026-07-07 16:36:40.737053-06	\N	\N	Daniel Larios Cárdenas No. 560, Int. B	\N	\N	\N	Guadalajara	Jalisco	44240	Mexico	44240	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
GUADALUPE MONSERRAT ARCE CORTES	GUADALUPE MONSERRAT ARCE CORTES	\N	monse.cortes@mycmetrology.com.mx	3313988168	\N	\N	\N	139	2026-07-07 13:28:01.941555-06	2026-07-07 16:36:43.71397-06	f	2026-07-07 16:36:43.716446-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Biobest México, S.A. de C.V.	Biobest México, S.A. de C.V.	\N	Quetzalli.Sanchez@biobestgroup.com	\N	\N	\N	\N	40	2026-07-07 13:28:01.67018-06	2026-07-07 16:36:32.610306-06	f	2026-07-07 16:36:32.61321-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
BONYARD SERVICIOS	BONYARD SERVICIOS	\N	calidad@bonyard.mx	\N	General de Ley de Personas Morales	\N	\N	36	2026-07-07 13:28:01.657444-06	2026-07-07 16:36:32.648176-06	f	2026-07-07 16:36:32.649791-06	\N	\N	EL Salto Via Verde KM- 9.2, El Salto	\N	\N	\N	El Salto	Jalisco	45686	Mexico	45686	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El Salto
Calza Garver, S.A. de C.V.	Calza Garver, S.A. de C.V.	\N	lesquivel@calzagarver.com	\N	General de Ley de Personas Morales	\N	\N	68	2026-07-07 13:28:01.753803-06	2026-07-07 16:36:32.746341-06	f	2026-07-07 16:36:32.748811-06	\N	\N	Calle 30 no 2739 Colonia Zona Industrial	\N	\N	\N	Guadalajara	Jalisco	44940	Mexico	44940	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Casa Tradición	Casa Tradición	\N	osmar.castro@claseazul.com	+52 33 1308 7348	Sin obligaciones fiscales	\N	\N	72	2026-07-07 13:28:01.763778-06	2026-07-07 16:36:36.426919-06	f	2026-07-07 16:36:36.430636-06	\N	\N	Amado Nervo 2200, Torre Bio N6 Int. 601, Jardines del Sol	\N	\N	\N	Zapopan	Jalisco	45050	Mexico	45050	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
CENTRO DE METROLOGÍA JUVA	CENTRO DE METROLOGÍA JUVA	\N	metrologiajuva@gmail.com	+52 33 1986 2264	General de Ley de Personas Morales	\N	\N	48	2026-07-07 13:28:01.69696-06	2026-07-07 16:36:36.511675-06	f	2026-07-07 16:36:36.513349-06	\N	\N	PROLONGACIÓN GONZALEZ GALLO 1847, INT 1, JEOVILLAS LOS OLIVOS 2	\N	\N	\N	SAN PEDRO TLAQUEPAQUE	Jalisco	45602	Mexico	45602	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	SAN PEDRO TLAQUEPAQUE
Cepi Especialistas en Proyectos contra Incendio, S.A. de C.V.	Cepi Especialistas en Proyectos contra Incendio, S.A. de C.V.	\N	mariorkoltik@gmail.com	+52 81 2374 8696	General de Ley de Personas Morales	\N	\N	76	2026-07-07 13:28:01.776282-06	2026-07-07 16:36:36.531574-06	f	2026-07-07 16:36:36.533707-06	\N	\N	Calle Vista Regia No. 500	\N	\N	\N	Guadalupe	Nuevo León	67123	Mexico	67123	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalupe
CMC METROLOGY	CMC METROLOGY	\N	msanchez@cmcmetrology.com	+52 614 102 6896	General de Ley de Personas Morales	\N	\N	52	2026-07-07 13:28:01.708984-06	2026-07-07 16:36:36.574535-06	f	2026-07-07 16:36:36.576436-06	\N	\N	PASEO HIDALGO DEL PARRAL 137-39B COL. PASEO DE CHIHUAHUA	\N	\N	\N	PARRAL	Chihuahua	31125	Mexico	31125	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	PARRAL
Comercial Automotriz del Noroeste S.A. de C.V.	Comercial Automotriz del Noroeste S.A. de C.V.	\N	346.adpc@plasanissan.com.mx	+52 667 328 5240	General de Ley de Personas Morales	\N	\N	80	2026-07-07 13:28:01.78789-06	2026-07-07 16:36:36.606153-06	f	2026-07-07 16:36:36.607433-06	\N	\N	Boulevard Emiliano Zapata Ote No. 156	\N	\N	\N	Culiacán	Sinaloa	80220	Mexico	80220	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Culiacán
comintec	comintec	\N	atencion_clientesgdl@comintec.com.mx	+52 33 2338 1031	General de Ley de Personas Morales	\N	\N	84	2026-07-07 13:28:01.798304-06	2026-07-07 16:36:36.64682-06	f	2026-07-07 16:36:36.648981-06	\N	\N	Emiliano Zapata 11	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45601	Mexico	45601	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
CONEXIONES	CONEXIONES	\N	\N	\N	\N	\N	\N	56	2026-07-07 13:28:01.719887-06	2026-07-07 16:36:36.703636-06	f	2026-07-07 16:36:36.705136-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Consultoria biomedica Integral	Consultoria biomedica Integral	\N	ventas@cobin.mx	+52 33 2106 7954	\N	\N	\N	88	2026-07-07 13:28:01.810334-06	2026-07-07 16:36:36.771433-06	f	2026-07-07 16:36:36.773146-06	\N	\N	Rodrigo de triana 2920	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
CONSULTORÍA BIOMEDICA INTEGRAL	CONSULTORÍA BIOMEDICA INTEGRAL	\N	facturacion@cobin.mx	+52 33 2106 7954	General de Ley de Personas Morales	\N	\N	60	2026-07-07 13:28:01.729695-06	2026-07-07 16:36:36.778188-06	f	2026-07-07 16:36:36.779806-06	\N	\N	RODRIGO DE TRIANA 2920, VALLARTA NORTE	\N	\N	\N	GUADALAJARA	Jalisco	44690	Mexico	44690	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
DULYMEX	DULYMEX	\N	calidad@dulymex.com.mx	+52 33 3612 9893	General de Ley de Personas Morales	\N	\N	92	2026-07-07 13:28:01.821976-06	2026-07-07 16:36:36.904065-06	f	2026-07-07 16:36:36.906103-06	\N	\N	CIRCUITO GRIJALVA 139-B	\N	\N	\N	TLAJOMULCO DE ZUÑIGA	Jalisco	45640	Mexico	45640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAJOMULCO DE ZUÑIGA
Ecochillers Corporation, S.A. de C.V.	Ecochillers Corporation, S.A. de C.V.	\N	teresa.santana@ecochillers.com	+52 33 2078 0336	General de Ley de Personas Morales	\N	\N	100	2026-07-07 13:28:01.842328-06	2026-07-07 16:36:36.946689-06	f	2026-07-07 16:36:36.949413-06	\N	\N	Av. Ramón Corona No. 645 Int. B	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45580	Mexico	45580	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
ELECTRIC ADVANCE	ELECTRIC ADVANCE	\N	\N	+52 33 2543 3475	General de Ley de Personas Morales	\N	\N	96	2026-07-07 13:28:01.831815-06	2026-07-07 16:36:36.961039-06	f	2026-07-07 16:36:36.96406-06	\N	\N	SAN FRANCISCO 1886 LA PALMIRA	\N	\N	\N	GUADALAJARA	Jalisco	45230	Mexico	45230	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Erika Valencia	Erika Valencia	\N	erika.valencia@biobestgroup.com	\N	\N	\N	\N	104	2026-07-07 13:28:01.851541-06	2026-07-07 16:36:40.262421-06	f	2026-07-07 16:36:40.26436-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Fabricación y manofactura de perfiles	Fabricación y manofactura de perfiles	\N	nleija@famaper.com	+52 81 4413 2704	General de Ley de Personas Morales	\N	\N	124	2026-07-07 13:28:01.903861-06	2026-07-07 16:36:40.326664-06	f	2026-07-07 16:36:40.328857-06	\N	\N	Blvd: Julian Treviño Elizondo #504, parque indsutrial san adnres.	\N	\N	\N	Apodaca	Nuevo León	66640	Mexico	66640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Apodaca
FANOSA SA DE CV	FANOSA SA DE CV	\N	liliana.mariscal@fanosa.com	+52 33 1894 8238	\N	\N	\N	108	2026-07-07 13:28:01.862716-06	2026-07-07 16:36:40.337792-06	f	2026-07-07 16:36:40.339092-06	\N	\N	AV. PRINCIPAL UNO No 8	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
FERRETERIA INDUSTRIAL ARENAS	FERRETERIA INDUSTRIAL ARENAS	\N	ventas10@ferreteriaarenas.com.mx	+52 33 1388 9123	General de Ley de Personas Morales	\N	\N	112	2026-07-07 13:28:01.873946-06	2026-07-07 16:36:40.38986-06	f	2026-07-07 16:36:40.391272-06	\N	\N	MIRLO 1269, MORELOS	\N	\N	\N	Guadalajara	Jalisco	44910	Mexico	44910	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
FISCALIA GENERAL DE LA REPUBLICA	FISCALIA GENERAL DE LA REPUBLICA	\N	violeta.valera@fgr.org.mx	+52 715 131 7279	General de Ley de Personas Morales	\N	\N	116	2026-07-07 13:28:01.883952-06	2026-07-07 16:36:40.449202-06	f	2026-07-07 16:36:40.452011-06	\N	\N	DR. VELAZCO #175 COL. DOCTORES CUAUHTEMOC CDMX	\N	\N	\N	CUAUHTEMOC	Ciudad de México	06720	Mexico	06720	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CUAUHTEMOC
Flosol Motors S.A. de C.V.	Flosol Motors S.A. de C.V.	\N	vcerna@flosolmotors.com	+52 33 3648 5253	General de Ley de Personas Morales	\N	\N	128	2026-07-07 13:28:01.913047-06	2026-07-07 16:36:40.489789-06	f	2026-07-07 16:36:40.491998-06	\N	\N	Eulogio Parra No. 2500	\N	\N	\N	Guadalajara	Jalisco	44657	Mexico	44657	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Foxconn	Foxconn	\N	luis.arcadia@gdl.fii-na.com	+52 33 3955 9033	General de Ley de Personas Morales	\N	\N	132	2026-07-07 13:28:01.923572-06	2026-07-07 16:36:40.55344-06	f	2026-07-07 16:36:40.555171-06	\N	\N	Del Bosque #1190	\N	\N	\N	Tlaquepaque	Jalisco	45590	Mexico	45590	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
FRESHCOURT	FRESHCOURT	\N	a.guzman@freshcourt.com	+52 452 147 9119	General de Ley de Personas Morales	\N	\N	120	2026-07-07 13:28:01.893709-06	2026-07-07 16:36:40.597231-06	f	2026-07-07 16:36:40.599322-06	\N	\N	EMPRESARIOS 135 7 C PUERTA DE HIERRO	\N	\N	\N	ZAPOPAN,	Jalisco	45116	Mexico	45116	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN,
GENERAL BRANDS MANOFACTURAS MEXICO	GENERAL BRANDS MANOFACTURAS MEXICO	\N	rbernal@sugarfoodsdemexico.com	+52 772 261 3513	General de Ley de Personas Morales	\N	\N	136	2026-07-07 13:28:01.933947-06	2026-07-07 16:36:40.642763-06	f	2026-07-07 16:36:40.64523-06	\N	\N	AVENIDA PARQUE MAZATLAN #5721	\N	\N	\N	MAZATLAN	Sinaloa	82204	Mexico	82204	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	MAZATLAN
General Electric	General Electric	\N	jose.sanchez5@gehalthcare.com	+52 55 5217 9725	\N	\N	\N	140	2026-07-07 13:28:01.943445-06	2026-07-07 16:36:40.655325-06	f	2026-07-07 16:36:40.656698-06	\N	\N	C. España Sn, 66640 Cdad. Apodaca, N.L.	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Grupo CPQ	Grupo CPQ	\N	yareni.razo@grupocpq.com	+52 33 1848 5437	General de Ley de Personas Morales	\N	\N	144	2026-07-07 13:28:01.951746-06	2026-07-07 16:36:40.774915-06	f	2026-07-07 16:36:40.776922-06	\N	\N	Calz Cedros 243, Col Cuidad Granja	\N	\N	\N	Zapopan	Jalisco	45010	Mexico	45010	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Gustinos	Gustinos	\N	compras3@gustinos.com	+52 33 3686 1771	General de Ley de Personas Morales	\N	\N	148	2026-07-07 13:28:01.960586-06	2026-07-07 16:36:43.730441-06	f	2026-07-07 16:36:43.733988-06	\N	\N	Calle Antiguo Camino Real de Colima	\N	\N	\N	San Agustín	Jalisco	45645	Mexico	45645	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Agustín
BORMANN	BORMANN	\N	\N	+52 81 8340 5067	General de Ley de Personas Morales	\N	\N	37	2026-07-07 13:28:01.660126-06	2026-07-07 16:36:32.658937-06	f	2026-07-07 16:36:32.660402-06	\N	\N	AV. COMETAS  # 170 ,COL. CONTRY	\N	\N	\N	MONTERREY	Nuevo León	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	MONTERREY
Calza Sider	Calza Sider	\N	calidad@calzasider.com	+52 33 3812 0198	General de Ley de Personas Morales	\N	\N	69	2026-07-07 13:28:01.756465-06	2026-07-07 16:36:32.75947-06	f	2026-07-07 16:36:32.761685-06	\N	\N	Calle 4 #2499, Zona industrial	\N	\N	\N	Guadalajara	Jalisco	44940	Mexico	44940	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
CAPYMETRO	CAPYMETRO	\N	\N	\N	General de Ley de Personas Morales	\N	\N	45	2026-07-07 13:28:01.689-06	2026-07-07 16:36:32.784169-06	f	2026-07-07 16:36:32.78549-06	\N	\N	\N	\N	\N	\N	CDMX	Ciudad de México	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CDMX
Casa Tradición Sa De Cv, Veronica Guzman	Casa Tradición Sa De Cv, Veronica Guzman	\N	veronica.guzman@claseazul.com	\N	General de Ley de Personas Morales	\N	\N	73	2026-07-07 13:28:01.766283-06	2026-07-07 16:36:36.445538-06	f	2026-07-07 16:36:36.45008-06	\N	\N	Carretera a ocotlan-tolotlan km 14 San martin de zula	\N	\N	\N	Ocotlan	Jalisco	47780	Mexico	47780	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Ocotlan
CENTRO LECHERO COOPERATIVO DE LOS ALTOS	CENTRO LECHERO COOPERATIVO DE LOS ALTOS	\N	cecoopalscl@hotmail.com	+52 378 712 0288	General de Ley de Personas Morales	\N	\N	49	2026-07-07 13:28:01.699714-06	2026-07-07 16:36:36.522048-06	f	2026-07-07 16:36:36.523393-06	\N	\N	EXTRAMUROS 525 CAPILLA DE GUADALUPE	\N	\N	\N	TEPATITLÁN	Jalisco	47700	Mexico	47700	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TEPATITLÁN
Cierres Automáticos National, S.A. de C.V.	Cierres Automáticos National, S.A. de C.V.	\N	\N	\N	General de Ley de Personas Morales	\N	\N	77	2026-07-07 13:28:01.778983-06	2026-07-07 16:36:36.563455-06	f	2026-07-07 16:36:36.565353-06	\N	\N	Paraiso 1681 Col. Del Fresno	\N	\N	\N	Guadalajara	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Comercializadora Ferretera Mtz, S.A. de C.V.	Comercializadora Ferretera Mtz, S.A. de C.V.	\N	kzepeda@cferreteramtz.com	\N	General de Ley de Personas Morales	\N	\N	81	2026-07-07 13:28:01.790407-06	2026-07-07 16:36:36.616797-06	f	2026-07-07 16:36:36.618719-06	\N	\N	HACIENDA CIENEGA DE MATA  2465	\N	\N	\N	Guadalajara	Jalisco	44720	Mexico	44720	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Compañía Tequilera Hacienda la Capilla, S.A. de C.V	Compañía Tequilera Hacienda la Capilla, S.A. de C.V	\N	sistente.compras@haciendalacapilla.com	+52 378 712 2200	General de Ley de Personas Morales	\N	\N	85	2026-07-07 13:28:01.801976-06	2026-07-07 16:36:36.659125-06	f	2026-07-07 16:36:36.66052-06	\N	\N	Hacienda No. 1	\N	\N	\N	Tepatitlán de Morelos	Jalisco	47700	Mexico	47700	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tepatitlán de Morelos
CONCRETOS CAYACAL	CONCRETOS CAYACAL	\N	calidad.concretoscayacal@outlook.com	\N	General de Ley de Personas Morales	\N	\N	53	2026-07-07 13:28:01.711356-06	2026-07-07 16:36:36.669964-06	f	2026-07-07 16:36:36.671434-06	\N	\N	ANDADOR LUIS GUITERREZ CORREA #67, PIE DE LA CASA	\N	\N	\N	LAZARO CARDENAS	Michoacán	60956	Mexico	60956	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	LAZARO CARDENAS
CONEXIONES INDUSTRIALES DE OCCIDENTE	CONEXIONES INDUSTRIALES DE OCCIDENTE	\N	ingenieria12@cioindustrial.com.mx	+52 33 1983 6581	General de Ley de Personas Morales	\N	\N	57	2026-07-07 13:28:01.722542-06	2026-07-07 16:36:36.71338-06	f	2026-07-07 16:36:36.71546-06	\N	\N	San Carlos 1683, Los Cajetes	\N	\N	\N	Zapopan	Jalisco	45234	Mexico	45234	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
CORPORATIVO GRUPO MEXLAB S.A. DE C.V.	CORPORATIVO GRUPO MEXLAB S.A. DE C.V.	\N	tecnovigilancia@grupomexlab.com	336342361	General de Ley de Personas Morales	\N	\N	61	2026-07-07 13:28:01.732486-06	2026-07-07 16:36:36.786475-06	f	2026-07-07 16:36:36.787735-06	\N	\N	Calle Susana Gómez Palafox No. 5486, Colonia Paseos del Sol 1A sección	\N	\N	\N	Zapopan	Jalisco	45079	Mexico	45079	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Coventry Bg S.A. de C.V.	Coventry Bg S.A. de C.V.	\N	maguilar@landroverpatria.mx	+52 322 274 0534	General de Ley de Personas Morales	\N	\N	89	2026-07-07 13:28:01.813312-06	2026-07-07 16:36:36.799908-06	f	2026-07-07 16:36:36.801092-06	\N	\N	Avenida Patria No. 2144	\N	\N	\N	Zapopan	Jalisco	45110	Mexico	45110	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
CUPER BIOSCIENCES	CUPER BIOSCIENCES	\N	\N	+52 55 4339 5035	General de Ley de Personas Morales	\N	\N	65	2026-07-07 13:28:01.744335-06	2026-07-07 16:36:36.84651-06	f	2026-07-07 16:36:36.849172-06	\N	\N	RENATTO LEDUC 122 TORIELLO GUERRA TLALPAN	\N	\N	\N	TLALPAN	Ciudad de México	14050	Mexico	14050	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLALPAN
Deprag México, S. de R.L. de C.V.	Deprag México, S. de R.L. de C.V.	\N	j.rodriguez@deprag.mx	+52 33 2834 0042	General de Ley de Personas Morales	\N	\N	93	2026-07-07 13:28:01.824664-06	2026-07-07 16:36:36.857791-06	f	2026-07-07 16:36:36.859393-06	\N	\N	Carretera a Nogales 4935 (West Plaza Park)	\N	\N	\N	Zapopan	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Electroconstrucciones de Ocotlan	Electroconstrucciones de Ocotlan	\N	\N	\N	\N	\N	\N	101	2026-07-07 13:28:01.844417-06	2026-07-07 16:36:40.202658-06	f	2026-07-07 16:36:40.205021-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
EQUIPOS Y BASCULAS INDUSTRIALES	EQUIPOS Y BASCULAS INDUSTRIALES	\N	direccion@basculasgallo.com.mx	+52 33 1411 4557	General de Ley de Personas Morales	\N	\N	97	2026-07-07 13:28:01.834456-06	2026-07-07 16:36:40.25188-06	f	2026-07-07 16:36:40.254197-06	\N	\N	FELIPE ANGELES 417	\N	\N	\N	GUADALAJARA	Jalisco	44740	Mexico	44740	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
EtCurae	EtCurae	\N	Compras@etcurae.com	\N	General de Ley de Personas Morales	\N	\N	105	2026-07-07 13:28:01.85393-06	2026-07-07 16:36:40.274223-06	f	2026-07-07 16:36:40.276124-06	\N	\N	Lázaro Cárdenas #500, Residencial San Agustín	\N	\N	\N	San Pedro Garza García	Nuevo León	66260	Mexico	66260	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Garza García
FANOSA SA DE CV, Belen Almaraz	FANOSA SA DE CV, Belen Almaraz	\N	maria.almaraz@fanosa.com	+52 384 733 3290	\N	\N	\N	109	2026-07-07 13:28:01.866175-06	2026-07-07 16:36:40.34666-06	f	2026-07-07 16:36:40.348558-06	\N	\N	AV. PRINCIPAL UNO No 8	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Farmacia del Carmen	Farmacia del Carmen	\N	\N	+52 33 3141 7010	General de Ley de Personas Morales	\N	\N	125	2026-07-07 13:28:01.906356-06	2026-07-07 16:36:40.357759-06	f	2026-07-07 16:36:40.359262-06	\N	\N	Dom. Jose Ma. Mercado 275	\N	\N	\N	Ahualulco del mercado	Jalisco	46730	Mexico	46730	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Ahualulco del mercado
FLEXIBLES IMPRESOS Y LAMINADOS PARA LA INDUSTRIA	FLEXIBLES IMPRESOS Y LAMINADOS PARA LA INDUSTRIA	\N	calidad@flexiempaques.mx	+52 33 1145 2782	General de Ley de Personas Morales	\N	\N	117	2026-07-07 13:28:01.886395-06	2026-07-07 16:36:40.462369-06	f	2026-07-07 16:36:40.464612-06	\N	\N	AV. LA LLAVE 1916	\N	\N	\N	TLAQUEPAQUE	Jalisco	45618	Mexico	45618	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAQUEPAQUE
Food Microbiology Laboratories	Food Microbiology Laboratories	\N	labmicrobiologyfood@gmail.com	33331196841	General de Ley de Personas Morales	\N	\N	129	2026-07-07 13:28:01.915791-06	2026-07-07 16:36:40.516802-06	f	2026-07-07 16:36:40.519206-06	\N	\N	Fundicion #2144 col. Parque Industrial El Alamo	\N	\N	\N	Guadalajara	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Francisco Javier Diaz Morales	Francisco Javier Diaz Morales	\N	\N	+52 33 1418 0013	General de Ley de Personas Morales	\N	\N	133	2026-07-07 13:28:01.926449-06	2026-07-07 16:36:40.576316-06	f	2026-07-07 16:36:40.577686-06	\N	\N	Tonala 96	\N	\N	\N	Tonala	Jalisco	45403	Mexico	45403	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tonala
FRIMAX CARROCERIAS	FRIMAX CARROCERIAS	\N	aux.compras@frimax.mx	+52 667 335 0924	General de Ley de Personas Morales	\N	\N	121	2026-07-07 13:28:01.89589-06	2026-07-07 16:36:40.609642-06	f	2026-07-07 16:36:40.611146-06	\N	\N	CAMINO A SANTA CRUZ DEL VALLE #121, VALLE DE LA MISERICORDIA	\N	\N	\N	SAN PEDRO TLAQUEPAQUE	Jalisco	45615	Mexico	45615	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	SAN PEDRO TLAQUEPAQUE
Global Aceros	Global Aceros	\N	compras1@globalaceros.mx	+52 33 3668 6770	General de Ley de Personas Morales	\N	\N	141	2026-07-07 13:28:01.945328-06	2026-07-07 16:36:40.688908-06	f	2026-07-07 16:36:40.690446-06	\N	\N	Periferico Sur #6290, Manuel Lopez Cotilla.	\N	\N	\N	Tlaquepaque	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
GPV Américas México, S.A.P.I. de C.V.	GPV Américas México, S.A.P.I. de C.V.	\N	Adriana.Noriega@gpv-group.com	+52 33 3369 2605	General de Ley de Personas Morales	\N	\N	137	2026-07-07 13:28:01.936817-06	2026-07-07 16:36:40.710364-06	f	2026-07-07 16:36:40.711932-06	\N	\N	Carretera Al Cucba No. 175, Int. 27	\N	\N	\N	Zapopan	Jalisco	45220	Mexico	45220	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
RICARDO IVAN RAMIREZ GARCIA	RICARDO IVAN RAMIREZ GARCIA	\N	servicios.muga@gmail.com	\N	General de Ley de Personas Morales	\N	\N	280	2026-07-07 13:28:02.231825-06	2026-07-07 16:36:51.234905-06	f	2026-07-07 16:36:51.236884-06	\N	\N	GENOFONTE #51, PASO BLANCO	\N	\N	\N	OCOTLAN	Jalisco	47810	Mexico	47810	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	OCOTLAN
CAB LOGISTICS	CAB LOGISTICS	\N	Lffregoso@pisa.com.mx	+52 33 2258 7089	General de Ley de Personas Morales	\N	\N	42	2026-07-07 13:28:01.677225-06	2026-07-07 16:36:32.683081-06	f	2026-07-07 16:36:32.685723-06	\N	\N	2, Av España 1788, Moderna	\N	\N	\N	Guadalajara	Jalisco	44190	Mexico	44190	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Calibraciones e Inspecciones CEISA	Calibraciones e Inspecciones CEISA	\N	\N	+52 921 267 7089	\N	\N	\N	66	2026-07-07 13:28:01.747501-06	2026-07-07 16:36:32.705923-06	f	2026-07-07 16:36:32.708057-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Capymet	Capymet	\N	lourdes.olvera@capymet.com	+52 686 190 2732	General de Ley de Personas Morales	\N	\N	70	2026-07-07 13:28:01.759249-06	2026-07-07 16:36:32.773936-06	f	2026-07-07 16:36:32.775925-06	\N	\N	Calle Niebla 3612, Nuevo Amanecer	\N	\N	\N	Mexicali	Baja California	21378	Mexico	21378	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Mexicali
Casa Tradición, Boga de Jesus Muñiz Gomez	Casa Tradición, Boga de Jesus Muñiz Gomez	\N	bogar.muniz@claseazul.com	\N	General de Ley de Personas Morales	\N	\N	74	2026-07-07 13:28:01.769513-06	2026-07-07 16:36:36.459641-06	f	2026-07-07 16:36:36.461339-06	\N	\N	Amado Nervo 2200, Torre Bio N6 Int. 601, Jardines del Sol	\N	\N	\N	Zapopan	Jalisco	45050	Mexico	45050	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
CEMSI (SERVICIO DE MANTENIMIENTO)	CEMSI (SERVICIO DE MANTENIMIENTO)	\N	hfuentes@cemsimexico.com	+52 33 1810 9334	General de Ley de Personas Morales	\N	\N	46	2026-07-07 13:28:01.692063-06	2026-07-07 16:36:36.480529-06	f	2026-07-07 16:36:36.482745-06	\N	\N	JOSE CARRILLO 3375, LOMAS DE POLANCO	\N	\N	\N	GUADALAJARA	Jalisco	44960	Mexico	44960	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
CFE	CFE	\N	mariana.ceja@cfe.mx	\N	General de Ley de Personas Morales	\N	\N	50	2026-07-07 13:28:01.702605-06	2026-07-07 16:36:36.543112-06	f	2026-07-07 16:36:36.544584-06	\N	\N	Av. Malinali S/N Col. Mesa Colorada Poniente	\N	\N	\N	Zapopan	Jalisco	45189	Mexico	45189	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Cohmedic, S.A. de C.V.	Cohmedic, S.A. de C.V.	\N	analistadecalidad@cohmedic.com	+52 33 3188 7807	General de Ley de Personas Morales	\N	\N	78	2026-07-07 13:28:01.782072-06	2026-07-07 16:36:36.586011-06	f	2026-07-07 16:36:36.587643-06	\N	\N	Justo Sierra No. 508-A	\N	\N	\N	Zapopan	Jalisco	45235	Mexico	45235	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Comercializadora Flexible, S.A. de C.V.	Comercializadora Flexible, S.A. de C.V.	\N	aalvarez@ecovismexico.com	+52 373 101 2618	General de Ley de Personas Morales	\N	\N	82	2026-07-07 13:28:01.792654-06	2026-07-07 16:36:36.626591-06	f	2026-07-07 16:36:36.627873-06	\N	\N	San Francisco 235	\N	\N	\N	Tlaquepaque	Jalisco	45615	Mexico	45615	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
CONCRETOS DCC	CONCRETOS DCC	\N	auxiliar.procesos@concretosdcc.com	\N	General de Ley de Personas Morales	\N	\N	54	2026-07-07 13:28:01.714114-06	2026-07-07 16:36:36.67971-06	f	2026-07-07 16:36:36.681687-06	\N	\N	km 1.2 Carretera Villa de Alvarez a Comala, Col. Las Aguilas	\N	\N	\N	Villa de Alvarez	Colima	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Villa de Alvarez
CONSIGUELO	CONSIGUELO	\N	administracion@consiguelo.mx	+52 33 1593 9735	General de Ley de Personas Morales	\N	\N	58	2026-07-07 13:28:01.725061-06	2026-07-07 16:36:36.724882-06	f	2026-07-07 16:36:36.726702-06	\N	\N	Av. Jesús Michel González #1275 int. 2	\N	\N	\N	Tlaquepaque	Jalisco	45601	Mexico	45601	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
Consocio Valsi	Consocio Valsi	\N	compras04@evasns.com.mx	+52 33 2339 4521	\N	\N	\N	86	2026-07-07 13:28:01.80476-06	2026-07-07 16:36:36.736138-06	f	2026-07-07 16:36:36.737879-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
CORRUGADOS HEAVY BOX	CORRUGADOS HEAVY BOX	\N	compras.sid@heavybox.com.mx	+52 33 3958 2261	General de Ley de Personas Morales	\N	\N	62	2026-07-07 13:28:01.735783-06	2026-07-07 16:36:36.793027-06	f	2026-07-07 16:36:36.794033-06	\N	\N	LAGO CAJITITLAN # 201 NICOLAS R CASILLAS	\N	\N	\N	TLAJOMULCO DE ZUÑIGA	Jalisco	45645	Mexico	45645	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAJOMULCO DE ZUÑIGA
Craf.	Craf.	\N	\N	\N	\N	\N	\N	90	2026-07-07 13:28:01.816173-06	2026-07-07 16:36:36.808923-06	f	2026-07-07 16:36:36.810557-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Electromedica Tinajero	Electromedica Tinajero	\N	cherrera@electromedicatinajero.com.mx	+52 33 1173 8069	General de Ley de Personas Morales	\N	\N	102	2026-07-07 13:28:01.846499-06	2026-07-07 16:36:40.219415-06	f	2026-07-07 16:36:40.222757-06	\N	\N	Domingo Sarmiento #2822 Int	\N	\N	\N	Guadalajara	Jalisco	44630	Mexico	44630	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
EURO STERN	EURO STERN	\N	\N	+52 33 3700 3141	General de Ley de Personas Morales	\N	\N	98	2026-07-07 13:28:01.836892-06	2026-07-07 16:36:40.285438-06	f	2026-07-07 16:36:40.287349-06	\N	\N	Vallarta 2760	\N	\N	\N	Guadalajara	Jalisco	44600	Mexico	44600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Eurostern Country	Eurostern Country	\N	lgaribay@eurostern.com.mx	+52 33 2725 7188	\N	\N	\N	106	2026-07-07 13:28:01.856444-06	2026-07-07 16:36:40.296028-06	f	2026-07-07 16:36:40.297548-06	\N	\N	\N	\N	\N	\N	Guadalajara	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
FARMACIA SANTIAGO-BARAJAS	FARMACIA SANTIAGO-BARAJAS	\N	kalifarmacia.mx@gmail.com	\N	General de Ley de Personas Morales	\N	\N	110	2026-07-07 13:28:01.868876-06	2026-07-07 16:36:40.369306-06	f	2026-07-07 16:36:40.370992-06	\N	\N	SAN FELIPE #554,GUADALAJARA CENTRO	\N	\N	\N	GUADALAJARA	Jalisco	44100	Mexico	44100	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
FGR Transformaciones Metálicas, S.A. de C.V.	FGR Transformaciones Metálicas, S.A. de C.V.	\N	mirna.rayas@fpi-isa.com	+52 442 592 3876	General de Ley de Personas Morales	\N	\N	114	2026-07-07 13:28:01.879155-06	2026-07-07 16:36:40.414015-06	f	2026-07-07 16:36:40.416468-06	\N	\N	Colinas de San José No. 3	\N	\N	\N	Querétaro	Querétaro	76117	Mexico	76117	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Querétaro
Firexpro de México, S. de R.L. de C.V.	Firexpro de México, S. de R.L. de C.V.	\N	servicios1@firexpro.com.mx	+52 33 2790 6022	General de Ley de Personas Morales	\N	\N	126	2026-07-07 13:28:01.908823-06	2026-07-07 16:36:40.426516-06	f	2026-07-07 16:36:40.428195-06	\N	\N	Nebulosa No.2828	\N	\N	\N	San pedro Tlaquepaque	Jalisco	45600	Mexico	45600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San pedro Tlaquepaque
FM INGENIEROS	FM INGENIEROS	\N	\N	\N	\N	\N	\N	118	2026-07-07 13:28:01.888987-06	2026-07-07 16:36:40.503208-06	f	2026-07-07 16:36:40.505569-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Food Microbiology Laboratories, Cristian Juarez	Food Microbiology Laboratories, Cristian Juarez	\N	cristian.juarez@foodmicrolab.com	\N	General de Ley de Personas Morales	\N	\N	130	2026-07-07 13:28:01.918472-06	2026-07-07 16:36:40.530658-06	f	2026-07-07 16:36:40.532835-06	\N	\N	Fundicion #2144 col. Parque Industrial El Alamo	\N	\N	\N	Guadalajara	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Francisco Javier Ordaz Higareda	Francisco Javier Ordaz Higareda	\N	\N	+52 341 117 6267	General de Ley de Personas Morales	\N	\N	134	2026-07-07 13:28:01.928866-06	2026-07-07 16:36:40.587202-06	f	2026-07-07 16:36:40.588685-06	\N	\N	Encino 13, San Antonio	\N	\N	\N	Tamazula	Jalisco	49652	Mexico	49652	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tamazula
FTECH	FTECH	\N	\N	\N	\N	\N	\N	122	2026-07-07 13:28:01.898032-06	2026-07-07 16:36:40.621168-06	f	2026-07-07 16:36:40.622703-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Gloria Leon Murillo	Gloria Leon Murillo	\N	\N	+52 33 1601 2194	General de Ley de Personas Morales	\N	\N	142	2026-07-07 13:28:01.947065-06	2026-07-07 16:36:40.699195-06	f	2026-07-07 16:36:40.701277-06	\N	\N	Francisco Javier Mina 757	\N	\N	\N	Guadalajara	Jalisco	44320	Mexico	44320	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
GRUPO AGC	GRUPO AGC	\N	ljauregui@grupoagc.com.mx	+52 33 3122 7826	General de Ley de Personas Morales	\N	\N	138	2026-07-07 13:28:01.939308-06	2026-07-07 16:36:40.722955-06	f	2026-07-07 16:36:40.724943-06	\N	\N	LAZARO CARDENAS 2825, ALAMO INDUSTRIAL	\N	\N	\N	GUADALAJARA	Jalisco	45593	Mexico	45593	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Grupo Collado	Grupo Collado	\N	yeni.gonzalez@gcollado.com	+52 33 3161 6254	General de Ley de Personas Morales	\N	\N	146	2026-07-07 13:28:01.955943-06	2026-07-07 16:36:40.759156-06	f	2026-07-07 16:36:40.761792-06	\N	\N	km. 23, carretera chapala 2001, Jal.	\N	\N	\N	\N	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
HARD ROCK HOTEL GUADALAJARA	HARD ROCK HOTEL GUADALAJARA	\N	\N	+52 33 3333 3000	General de Ley de Personas Morales	\N	\N	150	2026-07-07 13:28:01.964003-06	2026-07-07 16:36:43.775188-06	f	2026-07-07 16:36:43.777078-06	\N	\N	AV. IGNACIO VALLARTA 5145, COL. CAMINO REAL	\N	\N	\N	ZAPOPAN	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
Hennigues Automotive	Hennigues Automotive	\N	noel.cuevas@hennigesautomotive.com	+52 33 3377 9027	General de Ley de Personas Morales	\N	\N	158	2026-07-07 13:28:01.981632-06	2026-07-07 16:36:43.836679-06	f	2026-07-07 16:36:43.838406-06	\N	\N	Guadalajara’s Plant  Av. Paseo del Valle #4910	\N	\N	\N	Zapopan	Jalisco	45010	Mexico	45010	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
HULPAC	HULPAC	\N	gerentedeoperaciones@hulpac.com	\N	General de Ley de Personas Morales	\N	\N	154	2026-07-07 13:28:01.973096-06	2026-07-07 16:36:43.917552-06	f	2026-07-07 16:36:43.919718-06	\N	\N	CALLE DEL ANDEN #2415, INT. B, VALLE DEL ALAMO	\N	\N	\N	GUADALAJARA	Jalisco	44440	Mexico	44440	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
HARBISONWALKER INTERNATIONAL	HARBISONWALKER INTERNATIONAL	\N	mtrevino@thinkhwi.mx	\N	General de Ley de Personas Morales	\N	\N	149	2026-07-07 13:28:01.962286-06	2026-07-07 16:36:43.762233-06	f	2026-07-07 16:36:43.764795-06	\N	\N	CARR A COLOMBIA KM 23.2	\N	\N	\N	SALINAS VICTORIA	Nuevo León	65500	Mexico	65500	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	SALINAS VICTORIA
Hector Alejandro Ovalle Rendon, Other Address	Hector Alejandro Ovalle Rendon, Other Address	\N	\N	+52 33 3150 0963	General de Ley de Personas Morales	\N	\N	157	2026-07-07 13:28:01.979478-06	2026-07-07 16:36:43.802334-06	f	2026-07-07 16:36:43.804597-06	\N	\N	Cooperativa 21 de agosto 347	\N	\N	\N	Mazatlan	Sinaloa	82020	Mexico	82020	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Mazatlan
HONDA	HONDA	\N	\N	\N	\N	\N	\N	153	2026-07-07 13:28:01.970655-06	2026-07-07 16:36:43.8716-06	f	2026-07-07 16:36:43.873116-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Hospital San Javier, S.A. de C.V.	Hospital San Javier, S.A. de C.V.	\N	Vmperez@hospitalsanjavier.com	\N	General de Ley de Personas Morales	\N	\N	161	2026-07-07 13:28:01.988585-06	2026-07-07 16:36:43.894498-06	f	2026-07-07 16:36:43.896245-06	\N	\N	PABLO CASALES 640	\N	\N	\N	Guadalajara	\N	44670	Mexico	44670	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
IGNACIO GARCIA GARCIA	IGNACIO GARCIA GARCIA	\N	iggar48@gmail.com	\N	General de Ley de Personas Morales	\N	\N	165	2026-07-07 13:28:01.996972-06	2026-07-07 16:36:43.953074-06	f	2026-07-07 16:36:43.95464-06	\N	\N	DR. MANUEL RODRIGUEZ LAPUENTE 85	\N	\N	\N	guadalajara	Jalisco	44250	Mexico	44250	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	guadalajara
INDICO GRASO	INDICO GRASO	\N	\N	+52 33 1604 1833	General de Ley de Personas Morales	\N	\N	169	2026-07-07 13:28:02.005604-06	2026-07-07 16:36:44.001997-06	f	2026-07-07 16:36:44.004475-06	\N	\N	Lazaro Cardenas 372	\N	\N	\N	Tlaquepaque	Jalisco	45530	Mexico	45530	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
Infraestructura e Ingenieria 360	Infraestructura e Ingenieria 360	\N	\N	+52 33 1095 3643	General de Ley de Personas Morales	\N	\N	181	2026-07-07 13:28:02.02963-06	2026-07-07 16:36:44.054603-06	f	2026-07-07 16:36:44.056989-06	\N	\N	Lomas del Libano 3002	\N	\N	\N	Zapopan	Jalisco	45178	Mexico	45178	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
INGENIERIA ESPECIALIZADA EN EFICIENCIA ENERGETICA	INGENIERIA ESPECIALIZADA EN EFICIENCIA ENERGETICA	\N	gabriel.carraman@ie3.mx	+52 33 1670 0424	General de Ley de Personas Morales	\N	\N	173	2026-07-07 13:28:02.013415-06	2026-07-07 16:36:44.068203-06	f	2026-07-07 16:36:44.070502-06	\N	\N	CALLE AMBAR 2527	\N	\N	\N	GUADALAJARA	Jalisco	44560	Mexico	44560	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Instrumentos Industriales del Pacífico, S.A. de C.V.	Instrumentos Industriales del Pacífico, S.A. de C.V.	\N	leonardo.castaneda@iipsa.com	+52 668 816 0140	General de Ley de Personas Morales	\N	\N	185	2026-07-07 13:28:02.03858-06	2026-07-07 16:36:44.14685-06	f	2026-07-07 16:36:44.148937-06	\N	\N	Juan Carrasco No. 212 Pte.	\N	\N	\N	Los Mochis	Sinaloa	81200	Mexico	81200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Los Mochis
INVENTRONICS	INVENTRONICS	\N	a.siordia@inventronicsglobal.com	+52 33 2249 2693	General de Ley de Personas Morales	\N	\N	177	2026-07-07 13:28:02.022546-06	2026-07-07 16:36:44.157858-06	f	2026-07-07 16:36:44.159215-06	\N	\N	Parque Indsutrial FINSA, Carretera San Martin al Verde #520 Int. 8A	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45620	Mexico	45620	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
Jose Antonio Briseño Ortega	Jose Antonio Briseño Ortega	\N	\N	\N	\N	\N	\N	193	2026-07-07 13:28:02.055838-06	2026-07-07 16:36:44.285748-06	f	2026-07-07 16:36:44.287936-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
JOSE MANUEL AYALA DEL REAL	JOSE MANUEL AYALA DEL REAL	\N	j.manoayala@hotmail.com	+52 33 3189 2478	General de Ley de Personas Morales	\N	\N	189	2026-07-07 13:28:02.047766-06	2026-07-07 16:36:44.302006-06	f	2026-07-07 16:36:44.304285-06	\N	\N	PRIVADA DURAZNO 871, PARAISOS DEL COLI	\N	\N	\N	Zapopan	Jalisco	45069	Mexico	45069	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Kalex Transportes	Kalex Transportes	\N	sergio210295@gmail.com	+52 56 2005 0936	General de Ley de Personas Morales	\N	\N	197	2026-07-07 13:28:02.062904-06	2026-07-07 16:36:47.795587-06	f	2026-07-07 16:36:47.799227-06	\N	\N	Provenza Residencial	\N	\N	\N	San Agustín	Jalisco	45645	Mexico	45645	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Agustín
Lab Cor	Lab Cor	\N	eduardo_ramirez@leco.com	+52 33 2488 0705	General de Ley de Personas Morales	\N	\N	209	2026-07-07 13:28:02.086115-06	2026-07-07 16:36:47.85366-06	f	2026-07-07 16:36:47.856011-06	\N	\N	Los Pinos 19 - 4	\N	\N	\N	Zapopan	Jalisco	45138	Mexico	45138	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
LCP PINTURAS Y SERVICIOS INDUSTRIALES	LCP PINTURAS Y SERVICIOS INDUSTRIALES	\N	pinturasacuariodmzo@hotmail.com	+52 314 872 5026	General de Ley de Personas Morales	\N	\N	201	2026-07-07 13:28:02.070894-06	2026-07-07 16:36:47.940387-06	f	2026-07-07 16:36:47.942176-06	\N	\N	Miguel De La Madrid #100	\N	\N	\N	Manzanillo	Colima	28238	Mexico	28238	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Manzanillo
LSD DIAGNOSTICO DE ANALISIS CLINICOS	LSD DIAGNOSTICO DE ANALISIS CLINICOS	\N	yessica.ramirez@labosd.com	+52 462 220 9203	General de Ley de Personas Morales	\N	\N	205	2026-07-07 13:28:02.078774-06	2026-07-07 16:36:48.008614-06	f	2026-07-07 16:36:48.010051-06	\N	\N	FERNANDO ARANGUREN 840 ,BELENES NORTE,	\N	\N	\N	ZAPOPAN	Jalisco	45145	Mexico	45145	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
MANUEL MORA	MANUEL MORA	\N	moramanuel152@gmail.com	+52 991 446 3982	\N	\N	\N	217	2026-07-07 13:28:02.101554-06	2026-07-07 16:36:48.088346-06	f	2026-07-07 16:36:48.089676-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Margrey Oficial	Margrey Oficial	\N	jefecalidad@margrey.com.mx	+52 33 3663 1005	General de Ley de Personas Morales	\N	\N	229	2026-07-07 13:28:02.125937-06	2026-07-07 16:36:48.099281-06	f	2026-07-07 16:36:48.101639-06	\N	\N	Carr. A San Sebastian #1150-A, San Sebastianito	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45601	Mexico	45601	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
Medikal Muneris	Medikal Muneris	\N	especialista1@medikalmuneris.com	+52 33 1293 6702	\N	\N	\N	233	2026-07-07 13:28:02.133598-06	2026-07-07 16:36:48.164556-06	f	2026-07-07 16:36:48.166213-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Micropomex, S.A. de C.V.	Micropomex, S.A. de C.V.	\N	cmd2210@live.com.mx	+52 33 3735 5570	General de Ley de Personas Morales	\N	\N	237	2026-07-07 13:28:02.14305-06	2026-07-07 16:36:48.225771-06	f	2026-07-07 16:36:48.227334-06	\N	\N	San Juan No. 20	\N	\N	\N	Tlaquepaque	Jalisco	45520	Mexico	45520	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
MILENIO MOTORS	MILENIO MOTORS	\N	\N	+52 33 3832 2800	General de Ley de Personas Morales	\N	\N	221	2026-07-07 13:28:02.10938-06	2026-07-07 16:36:48.284747-06	f	2026-07-07 16:36:48.287151-06	\N	\N	PERIFERICO PONIENTE 2001 , COL. SAN JUAN DE OCOTAN	\N	\N	\N	ZAPOPAN	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
Mira de Occidente S.A. de C.V.	Mira de Occidente S.A. de C.V.	\N	compras@miraoccte.mx	+52 33 3810 1244	General de Ley de Personas Morales	\N	\N	241	2026-07-07 13:28:02.151445-06	2026-07-07 16:36:48.298062-06	f	2026-07-07 16:36:48.300502-06	\N	\N	Fresno No. 1781	\N	\N	\N	Guadalajara	Jalisco	44900	Mexico	44900	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
MUNSA MOLINOS	MUNSA MOLINOS	\N	comprasgdl@munsa.com.mx	\N	General de Ley de Personas Morales	\N	\N	225	2026-07-07 13:28:02.116919-06	2026-07-07 16:36:50.815262-06	f	2026-07-07 16:36:50.817359-06	\N	\N	AV. DE LAS TORRES 10000 PASEOS DE LOS OLIVOS	\N	\N	\N	Mazatlan	Sinaloa	82124	Mexico	82124	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Mazatlan
NAOSA COUNTRY	NAOSA COUNTRY	\N	\N	+52 33 3821 0651	General de Ley de Personas Morales	\N	\N	245	2026-07-07 13:28:02.159907-06	2026-07-07 16:36:50.827008-06	f	2026-07-07 16:36:50.828768-06	\N	\N	Av. Avila Camacho 1660, Col. Mezquitan Contry	\N	\N	\N	Guadalajara	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Naturesweet plaza zapotlan	Naturesweet plaza zapotlan	\N	\N	+52 341 117 6569	General de Ley de Personas Morales	\N	\N	253	2026-07-07 13:28:02.178327-06	2026-07-07 16:36:50.877416-06	f	2026-07-07 16:36:50.880057-06	\N	\N	Carretera Cd. Guzman - El Fresnito Km 1.0, Centro,	\N	\N	\N	CD Guzman	Jalisco	49000	Mexico	49000	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CD Guzman
NIRMAP	NIRMAP	\N	compras@nirmap.com	+52 938 164 4855	General de Ley de Personas Morales	\N	\N	249	2026-07-07 13:28:02.169287-06	2026-07-07 16:36:50.907669-06	f	2026-07-07 16:36:50.909097-06	\N	\N	CARRETERA CARMEN - PUERTO REAL KM 15, COL REUBICACIÓN	\N	\N	\N	CARMEN	Campeche	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CARMEN
Operadora Unidad de Investigacion en Salud de Chihuahua	Operadora Unidad de Investigacion en Salud de Chihuahua	\N	\N	+52 347 105 3435	General de Ley de Personas Morales	\N	\N	261	2026-07-07 13:28:02.195451-06	2026-07-07 16:36:50.979115-06	f	2026-07-07 16:36:50.980855-06	\N	\N	Av. Trasviña y Retes 1317	\N	\N	\N	Chihuahua	Chihuahua	31203	Mexico	31203	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Chihuahua
OSA CONTROL DE CALIDAD	OSA CONTROL DE CALIDAD	\N	gabriela.becerril@osacontroldecalidad.com	+52 33 3615 7569	General de Ley de Personas Morales	\N	\N	257	2026-07-07 13:28:02.187154-06	2026-07-07 16:36:51.013155-06	f	2026-07-07 16:36:51.015246-06	\N	\N	FRAY JUAN DE ZUMARRAGA 681 interior 1	\N	\N	\N	Zapopan	Jalisco	45040	Mexico	45040	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Hacienda la	Hacienda la	\N	\N	\N	\N	\N	\N	155	2026-07-07 13:28:01.975253-06	2026-07-07 16:36:43.747622-06	f	2026-07-07 16:36:43.750672-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
HENIGGUES AUTOMOTIVE	HENIGGUES AUTOMOTIVE	\N	\N	\N	\N	\N	\N	151	2026-07-07 13:28:01.966277-06	2026-07-07 16:36:43.814787-06	f	2026-07-07 16:36:43.816781-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
IB PACK	IB PACK	\N	Yavina@ibpack.mx	+52 33 3157 0138	General de Ley de Personas Morales	\N	\N	163	2026-07-07 13:28:01.993029-06	2026-07-07 16:36:43.930875-06	f	2026-07-07 16:36:43.932895-06	\N	\N	Avenida Adolfo López Mateos Sur 133	\N	\N	\N	Tlajomulco de zuñiga	Jalisco	45640	Mexico	45640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlajomulco de zuñiga
IMPULSORA INDUSTRIAL DE REFRIGERACION	IMPULSORA INDUSTRIAL DE REFRIGERACION	\N	maricela_rivera@ider.mx	+52 33 3836 0600	General de Ley de Personas Morales	\N	\N	167	2026-07-07 13:28:02.000877-06	2026-07-07 16:36:43.977395-06	f	2026-07-07 16:36:43.979436-06	\N	\N	CARRETERA A TESISTAN 8837	\N	\N	\N	TESISTAN	Jalisco	45200	Mexico	45200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TESISTAN
INDUSTRIAL DEVELOPMENT, CONTROL AND INSTRUMENTS	INDUSTRIAL DEVELOPMENT, CONTROL AND INSTRUMENTS	\N	administracion@industrialdci.com	+52 33 1133 9862	General de Ley de Personas Morales	\N	\N	171	2026-07-07 13:28:02.009665-06	2026-07-07 16:36:44.028803-06	f	2026-07-07 16:36:44.030706-06	\N	\N	FEDERALISMO 424 GUADALAJARA CENTRO	\N	\N	\N	Guadalajara	Jalisco	44100	Mexico	44100	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
INNOVACIONES FELWE	INNOVACIONES FELWE	\N	calzadomilegad@hotmail.com	+52 33 1862 7943	General de Ley de Personas Morales	\N	\N	175	2026-07-07 13:28:02.017909-06	2026-07-07 16:36:44.102147-06	f	2026-07-07 16:36:44.103664-06	\N	\N	PERIODISTAS #67,ALAMEDAS DE ZALATITAN	\N	\N	\N	TONALA	Jalisco	45405	Mexico	45405	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TONALA
Insofos, S.A.P.I. de C.V.	Insofos, S.A.P.I. de C.V.	\N	jcervantes@tormach.com	+52 33 1955 4906	General de Ley de Personas Morales	\N	\N	183	2026-07-07 13:28:02.033788-06	2026-07-07 16:36:44.123705-06	f	2026-07-07 16:36:44.12511-06	\N	\N	AV. INGLATERRA 5330-D	\N	\N	\N	ZAPOPAN	Jalisco	45222	Mexico	45222	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
IVAN JESUS LOPEZ MERTINEZ	IVAN JESUS LOPEZ MERTINEZ	\N	\N	\N	\N	\N	\N	179	2026-07-07 13:28:02.026384-06	2026-07-07 16:36:44.194939-06	f	2026-07-07 16:36:44.196785-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
JANETH PARRAL PLASCENCIA	JANETH PARRAL PLASCENCIA	\N	\N	\N	General de Ley de Personas Morales	\N	\N	187	2026-07-07 13:28:02.043161-06	2026-07-07 16:36:44.220051-06	f	2026-07-07 16:36:44.222075-06	\N	\N	LUIS C MEDINA 1821, JARDINES DEL AUDITORIO	\N	\N	\N	ZAPOPAN	Jalisco	45180	Mexico	45180	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
Jimena Garcia Alonso	Jimena Garcia Alonso	\N	\N	+52	General de Ley de Personas Morales	\N	\N	191	2026-07-07 13:28:02.052144-06	2026-07-07 16:36:44.236204-06	f	2026-07-07 16:36:44.238624-06	\N	\N	Juarez Norte 13	\N	\N	\N	tala	Jalisco	45345	Mexico	45345	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	tala
Juan Pablo Martínez Moreno	Juan Pablo Martínez Moreno	\N	61pablomtz@gmail.com	\N	\N	\N	\N	195	2026-07-07 13:28:02.059454-06	2026-07-07 16:36:44.351927-06	f	2026-07-07 16:36:44.353659-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Laboratorios Dibar	Laboratorios Dibar	\N	sup3@laboratoriosdibar.com	+52 443 779 9514	General de Ley de Personas Morales	\N	\N	211	2026-07-07 13:28:02.090951-06	2026-07-07 16:36:47.880672-06	f	2026-07-07 16:36:47.883168-06	\N	\N	Cedro #310, Los Angeles	\N	\N	\N	Morelia	Michoacán	58100	Mexico	58100	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Morelia
Lizen Autos, S.A. de C.V	Lizen Autos, S.A. de C.V	\N	\N	\N	General de Ley de Personas Morales	\N	\N	215	2026-07-07 13:28:02.098213-06	2026-07-07 16:36:47.974643-06	f	2026-07-07 16:36:47.976004-06	\N	\N	\N	\N	\N	\N	Zapopan	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
LIZEN PATRIA	LIZEN PATRIA	\N	ahernandez@vwpatria.mx	+52 33 1585 2724	General de Ley de Personas Morales	\N	\N	203	2026-07-07 13:28:02.075391-06	2026-07-07 16:36:47.985554-06	f	2026-07-07 16:36:47.987932-06	\N	\N	Av. Patria 2152, Santa Isabel	\N	\N	\N	Zapopan	Jalisco	45110	Mexico	45110	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
LUIS ANGEL MEDINA VILLAGRAN	LUIS ANGEL MEDINA VILLAGRAN	\N	ventas.gdl@serviciosmetrologicosmundiales.com	\N	\N	\N	\N	207	2026-07-07 13:28:02.082207-06	2026-07-07 16:36:48.031483-06	f	2026-07-07 16:36:48.033386-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Mecanoplastica Industrial S. de R.L. de C.V.	Mecanoplastica Industrial S. de R.L. de C.V.	\N	icalidad2@mecanoplastica.com.mx	+52 33 3330 9973	Sin obligaciones fiscales	\N	\N	231	2026-07-07 13:28:02.129262-06	2026-07-07 16:36:48.144238-06	f	2026-07-07 16:36:48.145818-06	\N	\N	Calzada Lazaro Cardenas #493, Int. A-12, Col. Ferrocarril, GDL Park	\N	\N	\N	Guadalajara	Jalisco	44440	Mexico	44440	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Megaventilación, S.A. de C.V.	Megaventilación, S.A. de C.V.	\N	compras@bigvento.com	+52 33 3617 6462	General de Ley de Personas Morales	\N	\N	235	2026-07-07 13:28:02.138304-06	2026-07-07 16:36:48.185778-06	f	2026-07-07 16:36:48.187573-06	\N	\N	San Cristóbal No. 130	\N	\N	\N	Zapopan	Jalisco	45170	Mexico	45170	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
METROLOGIA Y SERVICIOS MYC	METROLOGIA Y SERVICIOS MYC	\N	monse.cortes@serviciosmetrologicosmundiales.com	\N	General de Ley de Personas Morales	\N	\N	219	2026-07-07 13:28:02.105722-06	2026-07-07 16:36:48.19636-06	f	2026-07-07 16:36:48.197982-06	\N	\N	Av. Cristobal Colon 6086 Int. 57, Santa María Tequepexpan	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45601	Mexico	45601	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
Miguel F	Miguel F	\N	\N	\N	\N	\N	\N	239	2026-07-07 13:28:02.147187-06	2026-07-07 16:36:48.261163-06	f	2026-07-07 16:36:48.263019-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
MOTA ENGIL MÉXICO, S.A.P.I. DE C.V.	MOTA ENGIL MÉXICO, S.A.P.I. DE C.V.	\N	raul.lucio@mota-engil.com.mx	+52 55 4124 6400 ext. 1638	General de Ley de Personas Morales	\N	\N	223	2026-07-07 13:28:02.113463-06	2026-07-07 16:36:48.338301-06	f	2026-07-07 16:36:48.341082-06	\N	\N	Av. Rubén Darío 1533, Providencia 4a. Secc	\N	\N	\N	Guadalajara	Jalisco	44639	Mexico	44639	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Moti prints	Moti prints	\N	nrojas@motidigital.com	+52 33 3615 3370	General de Ley de Personas Morales	\N	\N	243	2026-07-07 13:28:02.155907-06	2026-07-07 16:36:48.353539-06	f	2026-07-07 16:36:48.355804-06	\N	\N	Mariano Azuela No. 7	\N	\N	\N	Guadalajara	Jalisco	44600	Mexico	44600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Naosa Volkswagen los Arcos	Naosa Volkswagen los Arcos	\N	gerenteservicioar@naosavw.com	+52 33 3502 4864	General de Ley de Personas Morales	\N	\N	251	2026-07-07 13:28:02.173165-06	2026-07-07 16:36:50.8414-06	f	2026-07-07 16:36:50.843805-06	\N	\N	Calzada Lazaro Cardena Poniente 2603	\N	\N	\N	Guadalajara	Jalisco	44530	Mexico	44530	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
NB Foods	NB Foods	\N	alejandra.soto@nbf.mx	+52 33 3310 0477	General de Ley de Personas Morales	\N	\N	247	2026-07-07 13:28:02.165216-06	2026-07-07 16:36:50.89052-06	f	2026-07-07 16:36:50.891678-06	\N	\N	Av. Jalisco 1924 Bodega 26. Col. San Francisco Tesistán, Capital, Parque Supe...	\N	\N	\N	Tesistán	Jalisco	45200	Mexico	45200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tesistán
Omnibus de México	Omnibus de México	\N	infraestructura_gdl@odm.com.mx	+52 55 5747 5844	General de Ley de Personas Morales	\N	\N	259	2026-07-07 13:28:02.191546-06	2026-07-07 16:36:50.947707-06	f	2026-07-07 16:36:50.949595-06	\N	\N	Republica de perú #301, Las Americas	\N	\N	\N	Aguascalientes	Aguascalientes	20230	Mexico	20230	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Aguascalientes
P&A Integrity Management Company, S.A. de C.V.	P&A Integrity Management Company, S.A. de C.V.	\N	\N	+52 33 3468 4767	General de Ley de Personas Morales	\N	\N	263	2026-07-07 13:28:02.199214-06	2026-07-07 16:36:51.031369-06	f	2026-07-07 16:36:51.033872-06	\N	\N	Acantilado No. 18	\N	\N	\N	Cuautitlán Izcalli	\N	54740	Mexico	54740	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Cuautitlán Izcalli
Pascual Enrique Ojeda Herrera	Pascual Enrique Ojeda Herrera	\N	hernan.contreras@lapisa.com	+52 352 526 1304	General de Ley de Personas Morales	\N	\N	199	2026-07-07 13:28:02.066924-06	2026-07-07 16:36:51.072798-06	f	2026-07-07 16:36:51.07414-06	\N	\N	Km. 5.5 la piedad-guad.	\N	\N	\N	La Piedad	Michoacán	59300	Mexico	59300	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	La Piedad
PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Alejandra Martínezi Cisneros	PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Alejandra Martínezi Cisneros	\N	alejandra.cisneros@vallenproveedora.com.mx	+52 446 139 0979	General de Ley de Personas Morales	\N	\N	267	2026-07-07 13:28:02.20747-06	2026-07-07 16:36:51.143408-06	f	2026-07-07 16:36:51.145157-06	\N	\N	BLVD. ADOLFO LOPEZ MATEOS 4000 UNIVERSIDAD PONIENTE TAMPICO, TAMAULIPAS. Méxi...	\N	\N	\N	Tampico	Tamaulipas	89336	Mexico	89336	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tampico
HERRAMIENTAS INDUSTRIALES GDL, S.A. de C.V.	HERRAMIENTAS INDUSTRIALES GDL, S.A. de C.V.	\N	mcontinuahbm@gmail.com	+52 33 3570 8015	General de Ley de Personas Morales	\N	\N	152	2026-07-07 13:28:01.968483-06	2026-07-07 16:36:43.848651-06	f	2026-07-07 16:36:43.850548-06	\N	\N	Canario #887 A Col. Morelos	\N	\N	\N	Guadalajara	Jalisco	44910	Mexico	44910	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Honda de México, S.A. de C.V.	Honda de México, S.A. de C.V.	\N	Erika_Padilla@hdm.honda.com	\N	General de Ley de Personas Morales	\N	\N	160	2026-07-07 13:28:01.986045-06	2026-07-07 16:36:43.882112-06	f	2026-07-07 16:36:43.884738-06	\N	\N	\N	\N	\N	\N	El Salto	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El Salto
IDSSA TECHNOLOGIES	IDSSA TECHNOLOGIES	\N	\N	+52 33 1326 3005	General de Ley de Personas Morales	\N	\N	164	2026-07-07 13:28:01.995252-06	2026-07-07 16:36:43.942217-06	f	2026-07-07 16:36:43.943622-06	\N	\N	C. CODRDOBA 2562, PROVIDENCIA	\N	\N	\N	GUADALAJARA	Jalisco	44630	Mexico	44630	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
INALFA	INALFA	\N	\N	\N	\N	\N	\N	168	2026-07-07 13:28:02.003147-06	2026-07-07 16:36:43.99002-06	f	2026-07-07 16:36:43.991573-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
INDUSTRIAS CABRERA	INDUSTRIAS CABRERA	\N	calidad@industriascabrera.com.mx	\N	General de Ley de Personas Morales	\N	\N	172	2026-07-07 13:28:02.011738-06	2026-07-07 16:36:44.040981-06	f	2026-07-07 16:36:44.042686-06	\N	\N	Carretera internacional a Nogales #8500, Col. Ciudad Granja	\N	\N	\N	Zapopan	Jalisco	45010	Mexico	45010	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
INNOVARE	INNOVARE	\N	biomedico@innovarecirugiaplastica.com	\N	General de Ley de Personas Morales	\N	\N	176	2026-07-07 13:28:02.019949-06	2026-07-07 16:36:44.11234-06	f	2026-07-07 16:36:44.114309-06	\N	\N	Av. Verona 7412, Fracc. Villa Verona	\N	\N	\N	ZAPOPAN	Jalisco	46136	Mexico	46136	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
IZUSU	IZUSU	\N	\N	+52 844 866 0890	\N	\N	\N	180	2026-07-07 13:28:02.027984-06	2026-07-07 16:36:44.207038-06	f	2026-07-07 16:36:44.208843-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Johnson Electric Group México, S. de R.L. de C.V.	Johnson Electric Group México, S. de R.L. de C.V.	\N	Walter.Gamez@johnsonelectric.com	\N	General de Ley de Personas Morales	\N	\N	192	2026-07-07 13:28:02.054085-06	2026-07-07 16:36:44.253839-06	f	2026-07-07 16:36:44.256482-06	\N	\N	Blvd. Morelos No. 1109	\N	\N	\N	Calera	Zacatecas	98519	Mexico	98519	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Calera
JORGE GALLO	JORGE GALLO	\N	\N	\N	\N	\N	\N	188	2026-07-07 13:28:02.045697-06	2026-07-07 16:36:44.269875-06	f	2026-07-07 16:36:44.272145-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
KANDYCO	KANDYCO	\N	sistemagestion@kandyco.com.mx	+52 33 1313 1193	General de Ley de Personas Morales	\N	\N	196	2026-07-07 13:28:02.061169-06	2026-07-07 16:36:47.813216-06	f	2026-07-07 16:36:47.816885-06	\N	\N	Otros datos fiscales COMERCIO EXTERIOR 1103 RINCON DE AGUA AZUL	\N	\N	\N	Guadalajara	Jalisco	44467	Mexico	44467	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
La Empresa de los Cien Años	La Empresa de los Cien Años	\N	\N	+52 33 1422 9591	General de Ley de Personas Morales	\N	\N	208	2026-07-07 13:28:02.084115-06	2026-07-07 16:36:47.828747-06	f	2026-07-07 16:36:47.831161-06	\N	\N	Av. Patria 1201, Uag,	\N	\N	\N	Zapopan	Jalisco	45110	Mexico	45110	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Laboratorios Zeyco	Laboratorios Zeyco	\N	wluciano@zeyco.mx	+52 477 393 6951	General de Ley de Personas Morales	\N	\N	212	2026-07-07 13:28:02.092749-06	2026-07-07 16:36:47.906465-06	f	2026-07-07 16:36:47.90877-06	\N	\N	CAMINO A SANTA ANA TEPATITLAN 2230 SANTA ANA TEPATITLAN	\N	\N	\N	Tlaquepaque	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
LAYCER	LAYCER	\N	laycerdavid@outlook.com	+52 33 1948 5336	\N	\N	\N	200	2026-07-07 13:28:02.068767-06	2026-07-07 16:36:47.929034-06	f	2026-07-07 16:36:47.930966-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
LOES INGENIEROS	LOES INGENIEROS	\N	\N	\N	General de Ley de Personas Morales	\N	\N	204	2026-07-07 13:28:02.077102-06	2026-07-07 16:36:47.997653-06	f	2026-07-07 16:36:47.999678-06	\N	\N	TUCIDIDES 87A	\N	\N	\N	GUADALAJARA	Jalisco	44690	Mexico	44690	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Mafain Integración Industrial, S.A. de C.V.	Mafain Integración Industrial, S.A. de C.V.	\N	mafainmexico@gmail.com	+52 33 3397 6651	General de Ley de Personas Morales	\N	\N	228	2026-07-07 13:28:02.124229-06	2026-07-07 16:36:48.067798-06	f	2026-07-07 16:36:48.069667-06	\N	\N	Francisco Sarabia No. 131	\N	\N	\N	Guadalajara	Jalisco	44730	Mexico	44730	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
MANOMETROS DE JALISCO	MANOMETROS DE JALISCO	\N	\N	+52 33 1126 2402	General de Ley de Personas Morales	\N	\N	216	2026-07-07 13:28:02.099817-06	2026-07-07 16:36:48.078079-06	f	2026-07-07 16:36:48.079692-06	\N	\N	federeación 685, Col. La perla	\N	\N	\N	Guadalajara	Jalisco	44360	Mexico	44360	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Medetic Corp	Medetic Corp	\N	administracion@medeticorp.com	+52 33 3129 8141	General de Ley de Personas Morales	\N	\N	232	2026-07-07 13:28:02.130902-06	2026-07-07 16:36:48.155375-06	f	2026-07-07 16:36:48.156731-06	\N	\N	Real acueducto 335	\N	\N	\N	Zapopan	Jalisco	45116	Mexico	45116	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Metrologia Zelkova	Metrologia Zelkova	\N	misael@metrologiazelkova.com	\N	General de Ley de Personas Morales	\N	\N	236	2026-07-07 13:28:02.140683-06	2026-07-07 16:36:48.215289-06	f	2026-07-07 16:36:48.217074-06	\N	\N	Oceano Pacifico 510	\N	\N	\N	Leon	Guanajuato	37520	Mexico	37520	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Leon
MIGUEL ANGEL MUÑOZ TORRES	MIGUEL ANGEL MUÑOZ TORRES	\N	miguel.munoz@serviciosmetrologicosmundiales.com	\N	\N	\N	\N	220	2026-07-07 13:28:02.107719-06	2026-07-07 16:36:48.248918-06	f	2026-07-07 16:36:48.251146-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Miguel Felipe Ordaz Higareda	Miguel Felipe Ordaz Higareda	\N	miguel.ordaz1111@gmail.com	+52 33 1193 1272	General de Ley de Personas Morales	\N	\N	240	2026-07-07 13:28:02.149273-06	2026-07-07 16:36:48.272406-06	f	2026-07-07 16:36:48.27385-06	\N	\N	Isla Martinica 2710	\N	\N	\N	Guadalajara	\N	44950	Mexico	44950	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Motidigital, nian zet rojas ramos	Motidigital, nian zet rojas ramos	\N	\N	\N	\N	\N	\N	244	2026-07-07 13:28:02.15792-06	2026-07-07 16:36:48.368779-06	f	2026-07-07 16:36:48.371034-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
MTQ DE MEXICO	MTQ DE MEXICO	\N	nancy.gonzalez@mtqmexico.com	+52 33 1138 6521	General de Ley de Personas Morales	\N	\N	224	2026-07-07 13:28:02.115089-06	2026-07-07 16:36:50.800216-06	f	2026-07-07 16:36:50.801627-06	\N	\N	José Maria Heredia 2405, lomas de guevara	\N	\N	\N	Guadalajara	Jalisco	44657	Mexico	44657	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Naturesweet Invernaderos, S. de R.L. de C.V.	Naturesweet Invernaderos, S. de R.L. de C.V.	\N	jmoreno@naturesweet.com	+52 33 3669 5580	General de Ley de Personas Morales	\N	\N	252	2026-07-07 13:28:02.175703-06	2026-07-07 16:36:50.867734-06	f	2026-07-07 16:36:50.869676-06	\N	\N	Av. Pablo Neruda No. 3041	\N	\N	\N	Guadalajara	Jalisco	44630	Mexico	44630	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
NG EXTRUSION	NG EXTRUSION	\N	\N	\N	\N	\N	\N	248	2026-07-07 13:28:02.167291-06	2026-07-07 16:36:50.898088-06	f	2026-07-07 16:36:50.899593-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Operadora Chivas	Operadora Chivas	\N	enrique.cruz@chivasdecorazon.com.mx	\N	General de Ley de Personas Morales	\N	\N	260	2026-07-07 13:28:02.193368-06	2026-07-07 16:36:50.958131-06	f	2026-07-07 16:36:50.959425-06	\N	\N	Inglaterra 3089 Vallarta Poniente	\N	\N	\N	Guadalajara	Jalisco	44110	Mexico	44110	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
OPKO Pharmaceuticals	OPKO Pharmaceuticals	\N	SCampos@opko.com	+52 33 3121 2761	General de Ley de Personas Morales	\N	\N	256	2026-07-07 13:28:02.185-06	2026-07-07 16:36:50.989981-06	f	2026-07-07 16:36:50.991341-06	\N	\N	Av. del niño obrero 651, Chapalita sur	\N	\N	\N	Guadalajara	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
PAMO DE OCCIDENTE	PAMO DE OCCIDENTE	\N	oscarjonatan2010@hotmail.com	+52 33 1413 8243	General de Ley de Personas Morales	\N	\N	264	2026-07-07 13:28:02.201281-06	2026-07-07 16:36:51.053383-06	f	2026-07-07 16:36:51.054594-06	\N	\N	TABACHIN 1453, PARAISOS DEL COLI	\N	\N	\N	ZAPOPAN	Jalisco	45069	Mexico	45069	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Omar  Chiquini Zamora	PROVEEDORA DE SEGURIDAD INDUSTRIAL DEL GOLFO, Omar  Chiquini Zamora	\N	OmarChiquiniZamora@eaton.com	+52 446 133 9416	General de Ley de Personas Morales	\N	\N	268	2026-07-07 13:28:02.209279-06	2026-07-07 16:36:51.155285-06	f	2026-07-07 16:36:51.157018-06	\N	\N	Avenida La Estacada #451	\N	\N	\N	Queretaro	Querétaro	00000	Mexico	00000	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Queretaro
Pym Proyectos y Montajes, S.A. de C.V .	Pym Proyectos y Montajes, S.A. de C.V .	\N	\N	+52 33 3809 1100	General de Ley de Personas Morales	\N	\N	276	2026-07-07 13:28:02.224768-06	2026-07-07 16:36:51.199251-06	f	2026-07-07 16:36:51.201344-06	\N	\N	Uruguay No. 2343	\N	\N	\N	Guadalajara	Jalisco	44920	Mexico	44920	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
IGNIS Servicios	IGNIS Servicios	\N	ignis.servicios@gmail.com	+52 311 233 8723	General de Ley de Personas Morales	\N	\N	166	2026-07-07 13:28:01.998755-06	2026-07-07 16:36:43.964229-06	f	2026-07-07 16:36:43.966669-06	\N	\N	Paseo de los cedros #104 Senderos de Tlaquepaque,	\N	\N	\N	Tlaquepaque	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
INDORAMA VENTURES	INDORAMA VENTURES	\N	jhernandez@mx.indorama.net	+52 33 3284 7209	\N	\N	\N	170	2026-07-07 13:28:02.007927-06	2026-07-07 16:36:44.017244-06	f	2026-07-07 16:36:44.019431-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Ingenieria Proyectos y Diseños	Ingenieria Proyectos y Diseños	\N	\N	+52 33 1134 0717	General de Ley de Personas Morales	\N	\N	182	2026-07-07 13:28:02.031562-06	2026-07-07 16:36:44.080359-06	f	2026-07-07 16:36:44.082363-06	\N	\N	Maquinistas 1384, Artesanos	\N	\N	\N	Tlaquepaque	Jalisco	45598	Mexico	45598	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
INGRASYS TECHNOLOGY MEXICO	INGRASYS TECHNOLOGY MEXICO	\N	esmeralda.lopez@fii-na.com	+52 33 3613 4881	\N	\N	\N	174	2026-07-07 13:28:02.015577-06	2026-07-07 16:36:44.091349-06	f	2026-07-07 16:36:44.093211-06	\N	\N	CARRETERA GUADALAJARA-EL SALTO, VIA EL VERDE No. 1900, INT. EDIF 08, COL. LAS...	\N	\N	\N	EL SALTO	\N	45690	Mexico	45690	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	EL SALTO
IPRODISA	IPRODISA	\N	arturoriosguzman@yahoo.com.mx	+52 33 3914 4069	General de Ley de Personas Morales	\N	\N	178	2026-07-07 13:28:02.024708-06	2026-07-07 16:36:44.169134-06	f	2026-07-07 16:36:44.171971-06	\N	\N	CAMINO A SANTA CRUZ DEL VALLE # 2439	\N	\N	\N	TLAQUEPAQUE	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAQUEPAQUE
Itesvia de Mexico S.A. de C.V.	Itesvia de Mexico S.A. de C.V.	\N	auxadmin@itesvia.com.mx	+52 33 3254 7014	General de Ley de Personas Morales	\N	\N	186	2026-07-07 13:28:02.040703-06	2026-07-07 16:36:44.18342-06	f	2026-07-07 16:36:44.18566-06	\N	\N	Lazaro Cardenas 2365	\N	\N	\N	Guadalajara	Jalisco	44440	Mexico	44440	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Jose María Godinez Enriquez	Jose María Godinez Enriquez	\N	servicios.godinez@gmail.com	+52 391 611 2312	General de Ley de Personas Morales	\N	\N	194	2026-07-07 13:28:02.057845-06	2026-07-07 16:36:44.319224-06	f	2026-07-07 16:36:44.321927-06	\N	\N	Constitución  #53, Libertad,	\N	\N	\N	Poncitlan	Jalisco	45950	Mexico	45950	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Poncitlan
JUAN PABLO MENDOZA ROMAN	JUAN PABLO MENDOZA ROMAN	\N	\N	\N	\N	\N	\N	190	2026-07-07 13:28:02.050357-06	2026-07-07 16:36:47.780443-06	f	2026-07-07 16:36:47.782988-06	\N	\N	Tecnicos 4819 Jardines de Guadalupe	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
LA FARMACIA DROGUERÍA	LA FARMACIA DROGUERÍA	\N	\N	\N	General de Ley de Personas Morales	\N	\N	198	2026-07-07 13:28:02.065259-06	2026-07-07 16:36:47.841742-06	f	2026-07-07 16:36:47.843707-06	\N	\N	CALLE LINDAVISTA 1850, LA LOMA	\N	\N	\N	GUADALAJARA	Jalisco	4800	Mexico	4800	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
LEONARDO AGUILAR LERMA	LEONARDO AGUILAR LERMA	\N	bandasleo5@gmail.com	+52 33 3605 0406	General de Ley de Personas Morales	\N	\N	202	2026-07-07 13:28:02.073274-06	2026-07-07 16:36:47.952518-06	f	2026-07-07 16:36:47.954338-06	\N	\N	Andador Cuervo	\N	\N	\N	Guadalajara	Jalisco	44910	Mexico	44910	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Lic. Georgette Hamden Muñoz	Lic. Georgette Hamden Muñoz	\N	georgetteham@hotmail.com	+52 33 2805 4409	General de Ley de Personas Morales	\N	\N	214	2026-07-07 13:28:02.096536-06	2026-07-07 16:36:47.96312-06	f	2026-07-07 16:36:47.965177-06	\N	\N	san Luis Gonzaga 4468 col camino real	\N	\N	\N	Zapopan	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
LSD DIAGNOSTICO DE ANALISIS CLINICOS, Luis Angel Rostro	LSD DIAGNOSTICO DE ANALISIS CLINICOS, Luis Angel Rostro	\N	compras@labosd.com	+52 462 100 3703	General de Ley de Personas Morales	\N	\N	206	2026-07-07 13:28:02.080423-06	2026-07-07 16:36:48.019672-06	f	2026-07-07 16:36:48.021403-06	\N	\N	FERNANDO ARANGUREN 840 ,BELENES NORTE,	\N	\N	\N	ZAPOPAN	Jalisco	45145	Mexico	45145	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
Madison Constructores	Madison Constructores	\N	\N	+52 33 3474 0685	General de Ley de Personas Morales	\N	\N	226	2026-07-07 13:28:02.119028-06	2026-07-07 16:36:48.042142-06	f	2026-07-07 16:36:48.043577-06	\N	\N	Vidrio # 5	\N	\N	\N	Tlaquepaque	Jalisco	45606	Mexico	45606	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
Mayoreo Ferretero Atlas	Mayoreo Ferretero Atlas	\N	ventasgrupo4@mayoreoferreroatlas.com	+52 33 5127 1932	General de Ley de Personas Morales	\N	\N	230	2026-07-07 13:28:02.127613-06	2026-07-07 16:36:48.122295-06	f	2026-07-07 16:36:48.123731-06	\N	\N	Independencia Sur 375	\N	\N	\N	Guadalajara	Jalisco	44450	Mexico	44450	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
MC Procesos en Papel y Cartón	MC Procesos en Papel y Cartón	\N	calidad@mcprocesos.com	+52 33 3693 6446	\N	\N	\N	218	2026-07-07 13:28:02.10341-06	2026-07-07 16:36:48.134414-06	f	2026-07-07 16:36:48.136437-06	\N	\N	Camino a Santa Ana Tepetitlan #2041, Col. Santa Ana Tepetitlan	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Medilab Diagnostico Medico Empresarial S. de R.L. de C.V.	Medilab Diagnostico Medico Empresarial S. de R.L. de C.V.	\N	ernesto.jimenez@bienestarempresarial.mx	+52 33 2604 2018	General de Ley de Personas Morales	\N	\N	234	2026-07-07 13:28:02.136199-06	2026-07-07 16:36:48.175367-06	f	2026-07-07 16:36:48.176734-06	\N	\N	Avenida Lapislazuli No. 2905	\N	\N	\N	Guadalajara	Jalisco	44560	Mexico	44560	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Migu	Migu	\N	\N	\N	\N	\N	\N	238	2026-07-07 13:28:02.145016-06	2026-07-07 16:36:48.236544-06	f	2026-07-07 16:36:48.238211-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Mitza Facturación	Mitza Facturación	\N	mitzi@comintec.com.mx	\N	\N	\N	\N	242	2026-07-07 13:28:02.153875-06	2026-07-07 16:36:48.309975-06	f	2026-07-07 16:36:48.3116-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
NATURAL SYRUP PRODUCER	NATURAL SYRUP PRODUCER	\N	kramos@nasyp.com.mx	\N	General de Ley de Personas Morales	\N	\N	246	2026-07-07 13:28:02.163001-06	2026-07-07 16:36:50.855507-06	f	2026-07-07 16:36:50.857418-06	\N	\N	CARRETERA (CARR.) GUADALAJARA - CHAPALA 9999 3 ZAPOTE DEL VALLE ZAPOTE DEL VALLE	\N	\N	\N	TLAJOMULCO DE ZUÑIGA	Jalisco	45672	Mexico	45672	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAJOMULCO DE ZUÑIGA
NUKUL Grupo Comercializador	NUKUL Grupo Comercializador	\N	compras@nukul.mx	+52 33 1804 2438	General de Ley de Personas Morales	\N	\N	250	2026-07-07 13:28:02.1712-06	2026-07-07 16:36:50.918024-06	f	2026-07-07 16:36:50.919796-06	\N	\N	Allende 25, Col. Los Gavilanes	\N	\N	\N	Tlajomulco de zuñiga	Jalisco	45645	Mexico	45645	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlajomulco de zuñiga
OLGA LIDIA CORTES VILLAGRAN	OLGA LIDIA CORTES VILLAGRAN	\N	olga.cortez@serviciosmetrologicosmundiales.com	\N	\N	\N	\N	254	2026-07-07 13:28:02.180537-06	2026-07-07 16:36:50.930028-06	f	2026-07-07 16:36:50.932056-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Omar Alejandro Aceves Camacho	Omar Alejandro Aceves Camacho	\N	jefeserviciosfarmaceuticos@hsmgdl.com	\N	\N	\N	\N	258	2026-07-07 13:28:02.189264-06	2026-07-07 16:36:50.939507-06	f	2026-07-07 16:36:50.940621-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Ortopedi Salud	Ortopedi Salud	\N	comprador4@ortopedisalud.com	+52 33 2071 0054	General de Ley de Personas Morales	\N	\N	262	2026-07-07 13:28:02.197102-06	2026-07-07 16:36:50.999756-06	f	2026-07-07 16:36:51.002213-06	\N	\N	Calle Volcán Paricutín 6593, Col. El Colli urbano	\N	\N	\N	Zapopan	Jalisco	45070	Mexico	45070	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Pack System, S.A. de C.V.	Pack System, S.A. de C.V.	\N	eduardo.davila@packsystem.com.mx	\N	General de Ley de Personas Morales	\N	\N	270	2026-07-07 13:28:02.213417-06	2026-07-07 16:36:51.04227-06	f	2026-07-07 16:36:51.043751-06	\N	\N	\N	\N	\N	\N	Tlajomulco de Zuñiga	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlajomulco de Zuñiga
Pont Aurell y Armengol MEXICO SA de CV	Pont Aurell y Armengol MEXICO SA de CV	\N	bdiazdeleon@pont-aurell.com	+52 449 894 9344	General de Ley de Personas Morales	\N	\N	274	2026-07-07 13:28:02.220597-06	2026-07-07 16:36:51.102432-06	f	2026-07-07 16:36:51.103973-06	\N	\N	Circuito Cerezos Sur #110 Parque industrial San Francisco  de los Romo.	\N	\N	\N	San Francisco de los Ramos	Aguascalientes	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Francisco de los Ramos
PROEMPAQUE	PROEMPAQUE	\N	calidad@proempaque.com	+52 449 140 2072	\N	\N	\N	266	2026-07-07 13:28:02.205461-06	2026-07-07 16:36:51.121746-06	f	2026-07-07 16:36:51.123041-06	\N	\N	Carr. San Luis Potosi 716, Bajío de las palmas	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Público general	Público general	\N	\N	000000000	\N	\N	\N	278	2026-07-07 13:28:02.228031-06	2026-07-07 16:36:51.188845-06	f	2026-07-07 16:36:51.19033-06	\N	\N	Sin domicilio s/n	\N	\N	\N	general	\N	00000	Mexico	00000	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	general
RY Candy, S.A. de C.V.	RY Candy, S.A. de C.V.	\N	seguridad.industrial@rycandy.com	+52 33 3836 3700	General de Ley de Personas Morales	\N	\N	282	2026-07-07 13:28:02.235309-06	2026-07-07 16:36:51.325634-06	f	2026-07-07 16:36:51.328433-06	\N	\N	López Cotilla No. 296	\N	\N	\N	Tonalá	Jalisco	45408	Mexico	45408	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tonalá
asesores sire	asesores sire	\N	\N	\N	\N	\N	\N	361	2026-07-07 13:28:02.430881-06	2026-07-07 16:36:32.387786-06	f	2026-07-07 16:36:32.389708-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
gerentecalidad@margrey.com.mx	gerentecalidad@margrey.com.mx	\N	gerentecalidad@margrey.com.mx	\N	\N	\N	\N	365	2026-07-07 13:28:02.440127-06	2026-07-07 16:36:40.67693-06	f	2026-07-07 16:36:40.679105-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
mario.munoz@fgr.org.mx	mario.munoz@fgr.org.mx	\N	mario.munoz@fgr.org.mx	\N	\N	\N	\N	369	2026-07-07 13:28:02.446634-06	2026-07-07 16:36:48.111222-06	f	2026-07-07 16:36:48.113085-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Pigore Ingenieria	Pigore Ingenieria	\N	compras@piogere.com.mx	+52 33 1874 0007	General de Ley de Personas Morales	\N	\N	273	2026-07-07 13:28:02.218478-06	2026-07-07 16:36:51.093297-06	f	2026-07-07 16:36:51.094958-06	\N	\N	Agustín Rivera, Int. #1, Ext. #200	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45600	Mexico	45600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
POSTES Y PRECOLADOS INDUSTRIALES	POSTES Y PRECOLADOS INDUSTRIALES	\N	administracion@ppinsa.com.mx	+52 492 225 1915	General de Ley de Personas Morales	\N	\N	265	2026-07-07 13:28:02.203349-06	2026-07-07 16:36:51.112092-06	f	2026-07-07 16:36:51.113891-06	\N	\N	MORELOS 1105 MEGA PARQUE INDUSTRIAL AEREOPUERTO DE LA CALERA	\N	\N	\N	ZACATECAS	Zacatecas	98519	Mexico	98519	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZACATECAS
PROYECTOS Y VALIDACIONES SORIMTEC	PROYECTOS Y VALIDACIONES SORIMTEC	\N	\N	+52 33 3183 7229	General de Ley de Personas Morales	\N	\N	269	2026-07-07 13:28:02.210993-06	2026-07-07 16:36:51.165395-06	f	2026-07-07 16:36:51.166988-06	\N	\N	PIÑON 88, LOMAS DE SAN MATEO	\N	\N	\N	NAUCALPAN DE JUAREZ	México	53200	Mexico	53200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	NAUCALPAN DE JUAREZ
Público	Público	\N	calidad@sisc-comedores.com	+52 33 3723 9003	\N	\N	\N	277	2026-07-07 13:28:02.226377-06	2026-07-07 16:36:51.176578-06	f	2026-07-07 16:36:51.178658-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Rinoinovation, S.A. de C.V.	Rinoinovation, S.A. de C.V.	\N	rinotrack@hotmail.com	+52 33 2358 4299	General de Ley de Personas Morales	\N	\N	285	2026-07-07 13:28:02.241794-06	2026-07-07 16:36:51.259721-06	f	2026-07-07 16:36:51.262428-06	\N	\N	Retorno No. 3	\N	\N	\N	El Salto	Jalisco	45693	Mexico	45693	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El Salto
ROSA MARIA MURILLO MACIAS	ROSA MARIA MURILLO MACIAS	\N	facturascm.gdl@gmail.com	+52 33 1430 3003	General de Ley de Personas Morales	\N	\N	281	2026-07-07 13:28:02.23349-06	2026-07-07 16:36:51.2855-06	f	2026-07-07 16:36:51.28728-06	\N	\N	Leona Vicario #22-A,Santa Ana Tepetitlan.	\N	\N	\N	Zapopan	Jalisco	45230	Mexico	45230	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
SAM MOTORS DE TORREON	SAM MOTORS DE TORREON	\N	\N	\N	General de Ley de Personas Morales	\N	\N	289	2026-07-07 13:28:02.248553-06	2026-07-07 16:36:51.352873-06	f	2026-07-07 16:36:51.35488-06	\N	\N	BLVD. INDEPENDENCIA # 502 OTE COL. CENTRO	\N	\N	\N	TORREON	Coahuila	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TORREON
Sánchez y Martín, S.A. de C.V.	Sánchez y Martín, S.A. de C.V.	\N	orodriguez@sym.com.mx	+52 33 3540 2424	General de Ley de Personas Morales	\N	\N	329	2026-07-07 13:28:02.366012-06	2026-07-07 16:36:54.094901-06	f	2026-07-07 16:36:54.097952-06	\N	\N	Av. Vallarta No. 3298, Piso 7	\N	\N	\N	Guadalajara	Jalisco	44690	Mexico	44690	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Sandvik Mining and Construction de México, S.A. de C.V.	Sandvik Mining and Construction de México, S.A. de C.V.	\N	alejandra.luna_c@sandvik.com	+52 33 3601 0362	General de Ley de Personas Morales	\N	\N	309	2026-07-07 13:28:02.324365-06	2026-07-07 16:36:54.126134-06	f	2026-07-07 16:36:54.128531-06	\N	\N	Benjamin Franklin Mz. 10 Lt. 8	\N	\N	\N	Tlajomulco de Zúñiga	Jalisco	45640	Mexico	45640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlajomulco de Zúñiga
SANMINA	SANMINA	\N	rosendo.larios@sanmina.com	+52 33 2243 8664	General de Ley de Personas Morales	\N	\N	293	2026-07-07 13:28:02.256222-06	2026-07-07 16:36:54.155254-06	f	2026-07-07 16:36:54.156327-06	\N	\N	CARR GDL-CHAPALA KM 15.5 #97,	\N	\N	\N	GUADALAJARA	Jalisco	45650	Mexico	45650	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Sanwa Screen Mexico, S.A. de C.V.	Sanwa Screen Mexico, S.A. de C.V.	\N	jose-gomez@smx.sanwag.com	+52 33 3364 1404	General de Ley de Personas Morales	\N	\N	313	2026-07-07 13:28:02.332175-06	2026-07-07 16:36:54.173002-06	f	2026-07-07 16:36:54.174514-06	\N	\N	Av. Dr. Angel Leaño No. 401, Nave 17	\N	\N	\N	Zapopan	Jalisco	45134	Mexico	45134	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Semillas y Cereales San Juanico	Semillas y Cereales San Juanico	\N	calidad@sanjuanico.com.mx	+52 951 220 8540	General de Ley de Personas Morales	\N	\N	317	2026-07-07 13:28:02.342015-06	2026-07-07 16:36:54.257838-06	f	2026-07-07 16:36:54.25908-06	\N	\N	Jesus Aguilar Días #23-A, San Agustin	\N	\N	\N	Tlajomulco de Zuñiga	Jalisco	45645	Mexico	45645	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlajomulco de Zuñiga
SERVIEMPAQUES 3G	SERVIEMPAQUES 3G	\N	gerencia@maderasguadalupana.com	+52 33 1429 8240	General de Ley de Personas Morales	\N	\N	297	2026-07-07 13:28:02.26339-06	2026-07-07 16:36:54.290278-06	f	2026-07-07 16:36:54.291682-06	\N	\N	Jose Maria Morelos 187	\N	\N	\N	El Salto	Jalisco	45693	Mexico	45693	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El Salto
Shanaturals	Shanaturals	\N	formulacioncp@shanaturals.com	+52 33 3171 2339	General de Ley de Personas Morales	\N	\N	321	2026-07-07 13:28:02.350755-06	2026-07-07 16:36:54.310646-06	f	2026-07-07 16:36:54.312348-06	\N	\N	Av.Tabachines 3514,Loma Bonita Ejidal	\N	\N	\N	Zapopan	Jalisco	45085	Mexico	45085	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Sistema de Tren Eléctrico Urbano	Sistema de Tren Eléctrico Urbano	\N	rcuevas@siteur.gob.mx	+52 33 3811 1548	General de Ley de Personas Morales	\N	\N	325	2026-07-07 13:28:02.359011-06	2026-07-07 16:36:54.389376-06	f	2026-07-07 16:36:54.390956-06	\N	\N	Calle Andres Bello 4450	\N	\N	\N	Guadalajara	Jalisco	44950	Mexico	44950	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
SOLAR PANEL COMPANY	SOLAR PANEL COMPANY	\N	spanel065@gmail.com	+52 951 364 8916	General de Ley de Personas Morales	\N	\N	301	2026-07-07 13:28:02.271868-06	2026-07-07 16:36:54.423566-06	f	2026-07-07 16:36:54.424969-06	\N	\N	VISTA DE LAS LOMAS #49, INT: 7	\N	\N	\N	TLAJOMULCO DE ZUÑIGA	Jalisco	45645	Mexico	45645	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAJOMULCO DE ZUÑIGA
SS AUTOMAT	SS AUTOMAT	\N	cobranza@ssautomat.com.mx	+52 33 1200 9978	General de Ley de Personas Morales	\N	\N	305	2026-07-07 13:28:02.314845-06	2026-07-07 16:36:54.469397-06	f	2026-07-07 16:36:54.471142-06	\N	\N	NIÑOS HEROES 1207, COL. MODERNA	\N	\N	\N	GUADALAJARA	Jalisco	44190	Mexico	44190	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Technology & Steel, S.A. de C.V.	Technology & Steel, S.A. de C.V.	\N	compras@technologysteel.com	+52 33 2643 6052	General de Ley de Personas Morales	\N	\N	337	2026-07-07 13:28:02.383494-06	2026-07-07 16:36:54.537668-06	f	2026-07-07 16:36:54.53924-06	\N	\N	Cruz del Sur No. 3297	\N	\N	\N	Zapopan	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
TECNOLOGIAS COMINTEC, Lorena Flores	TECNOLOGIAS COMINTEC, Lorena Flores	\N	atencion_clientesgdl3@comintec.com.mx	+52 33 2338 1031	General de Ley de Personas Morales	\N	\N	333	2026-07-07 13:28:02.374626-06	2026-07-07 16:36:54.601123-06	f	2026-07-07 16:36:54.603392-06	\N	\N	AURORA BOREAL # 3966 COL. ARBOLEDAS	\N	\N	\N	Zapopan	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Trescal Calibración México S.A. de C.V.	Trescal Calibración México S.A. de C.V.	\N	Dana.Gratacos@trescal.com	+52 446 139 3393	General de Ley de Personas Morales	\N	\N	341	2026-07-07 13:28:02.392547-06	2026-07-07 16:36:57.53528-06	f	2026-07-07 16:36:57.537988-06	\N	\N	Avenida Colinas del Cimatario 381	\N	\N	\N	Querétaro	Querétaro	76090	Mexico	76090	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Querétaro
Universal Wipes	Universal Wipes	\N	vanessa.castellanos@uwicorp.com	+52 378 186 8564	General de Ley de Personas Morales	\N	\N	345	2026-07-07 13:28:02.400014-06	2026-07-07 16:36:57.595046-06	f	2026-07-07 16:36:57.598785-06	\N	\N	Carretera Tepatitlan-Yahualica Km 8	\N	\N	\N	Tepatitlán de Morelos	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tepatitlán de Morelos
WONDER FOODS MEXICO	WONDER FOODS MEXICO	\N	aarambula@wonderfoods.mx	+52 33 3796 1213	General de Ley de Personas Morales	\N	\N	353	2026-07-07 13:28:02.415312-06	2026-07-07 16:36:57.734436-06	f	2026-07-07 16:36:57.736371-06	\N	\N	PRIVADA DE LAS MAGNOLIAS #70	\N	\N	\N	tlajomulco de zuñiga	Jalisco	45640	Mexico	45640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	tlajomulco de zuñiga
YUTOTECH	YUTOTECH	\N	PERLA.MORENO@szyuto.com	+52 33 2253 4055	General de Ley de Personas Morales	\N	\N	357	2026-07-07 13:28:02.423409-06	2026-07-07 16:36:57.755554-06	f	2026-07-07 16:36:57.756949-06	\N	\N	Carretera Guadalajara - Chapala # 303, Kampus Industrial Santa Rosa, Huerta V...	\N	\N	\N	Ixtlahuacán de los Membrillos	Jalisco	45850	Mexico	45850	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Ixtlahuacán de los Membrillos
diprocat	diprocat	\N	minervadiprocat@gmail.com	+52 33 2507 4880	General de Ley de Personas Morales	\N	\N	363	2026-07-07 13:28:02.435347-06	2026-07-07 16:36:36.871795-06	f	2026-07-07 16:36:36.8737-06	\N	\N	Francisco Javier Mina 207	\N	\N	\N	Puente de Ixtla	Morelos	62660	Mexico	62660	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Puente de Ixtla
joselyne.barron@uwipes.com	joselyne.barron@uwipes.com	\N	joselyne.barron@uwipes.com	\N	\N	\N	\N	367	2026-07-07 13:28:02.443524-06	2026-07-07 16:36:44.338368-06	f	2026-07-07 16:36:44.340484-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Panakos Plasma Marino, S.A. de C.V.	Panakos Plasma Marino, S.A. de C.V.	\N	Israel.sarabia@panakosplasmamarino.com	+52 33 2637 4612	General de Ley de Personas Morales	\N	\N	271	2026-07-07 13:28:02.215014-06	2026-07-07 16:36:51.061129-06	f	2026-07-07 16:36:51.063013-06	\N	\N	Av. Jalisco No. 9500 Int. 7	\N	\N	\N	Zapopan	Jalisco	45200	Mexico	45200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Proveedora Comercial Alteña, S.A. de C.V.	Proveedora Comercial Alteña, S.A. de C.V.	\N	\N	\N	General de Ley de Personas Morales	\N	\N	275	2026-07-07 13:28:02.222785-06	2026-07-07 16:36:51.134044-06	f	2026-07-07 16:36:51.135831-06	\N	\N	\N	\N	\N	\N	Tepatitlán de Morelos	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tepatitlán de Morelos
Raul Morales Orta	Raul Morales Orta	\N	raul.morales@myhconsultores.com	\N	\N	\N	\N	283	2026-07-07 13:28:02.237656-06	2026-07-07 16:36:51.212426-06	f	2026-07-07 16:36:51.21449-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
REYPCO REFRIGERACION Y PARTES PARA COMPRESORES SA DE CV	REYPCO REFRIGERACION Y PARTES PARA COMPRESORES SA DE CV	\N	marco_nuno@reypco.com	+52 33 1707 9566	\N	\N	\N	279	2026-07-07 13:28:02.229585-06	2026-07-07 16:36:51.224202-06	f	2026-07-07 16:36:51.225591-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Rota Impresos Nueva Galicia, S.A. de C.V.	Rota Impresos Nueva Galicia, S.A. de C.V.	\N	\N	\N	General de Ley de Personas Morales	\N	\N	287	2026-07-07 13:28:02.245484-06	2026-07-07 16:36:51.299491-06	f	2026-07-07 16:36:51.301893-06	\N	\N	Torrecillas 1949A	\N	\N	\N	Guadalajara	\N	44870	Mexico	44870	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
SAMFRUT	SAMFRUT	\N	aseguramientodecalidad@samfrut.com.mx	+52 351 115 0366	General de Ley de Personas Morales	\N	\N	291	2026-07-07 13:28:02.252102-06	2026-07-07 16:36:54.079085-06	f	2026-07-07 16:36:54.081824-06	\N	\N	BACHILLERES 15 EJIDAL	\N	\N	\N	JACONA	Michoacán	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	JACONA
Sane Foods	Sane Foods	\N	antonio.mendez@sane.com.mx	+52 33 3814 8040	General de Ley de Personas Morales	\N	\N	311	2026-07-07 13:28:02.328276-06	2026-07-07 16:36:54.146073-06	f	2026-07-07 16:36:54.14817-06	\N	\N	Carretera Chapala - Guadalajara KM 1.5	\N	\N	\N	Chapala	Jalisco	45900	Mexico	45900	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Chapala
SAVERGLASS	SAVERGLASS	\N	ngs@saverglass.com	+52 33 3905 3661	Sin obligaciones fiscales	\N	\N	295	2026-07-07 13:28:02.259786-06	2026-07-07 16:36:54.192569-06	f	2026-07-07 16:36:54.19422-06	\N	\N	VIALIDAD 201 PARQUE INDUSTRIAL CENTRO LOGISTICO DE JALISCO KM 11.034 CORRETERA	\N	\N	\N	ACATLAN DE JUAREZ	Jalisco	45050	Mexico	45050	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ACATLAN DE JUAREZ
Schenker International, S.A. de C.V.	Schenker International, S.A. de C.V.	\N	alejandro.leon@dbschenker.com	+52 55 8869 4954	General de Ley de Personas Morales	\N	\N	315	2026-07-07 13:28:02.337482-06	2026-07-07 16:36:54.215873-06	f	2026-07-07 16:36:54.217775-06	\N	\N	Av. Patriotismo No. 201, Piso 3	\N	\N	\N	Mexico	Ciudad de México	03800	Mexico	03800	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Mexico
Servicios Profesionales Sor, S.A. de C.V.	Servicios Profesionales Sor, S.A. de C.V.	\N	auxmantenimiento@serviciosprofesionalessor.com.mx	+52 33 3777 1100	General de Ley de Personas Morales	\N	\N	319	2026-07-07 13:28:02.346208-06	2026-07-07 16:36:54.27802-06	f	2026-07-07 16:36:54.28-06	\N	\N	Antiguo camino San Juan de Ocotán No. 395	\N	\N	\N	Zapopan	Jalisco	45019	Mexico	45019	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Sialico	Sialico	\N	j.perez@sialico.com	+52 222 429 4350	General de Ley de Personas Morales	\N	\N	323	2026-07-07 13:28:02.355233-06	2026-07-07 16:36:54.33191-06	f	2026-07-07 16:36:54.333838-06	\N	\N	C. Huamantla 55, La Paz	\N	\N	\N	Heroica	Puebla	72160	Mexico	72160	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Heroica
SINCOF INGENIERIA	SINCOF INGENIERIA	\N	compras@sincofingenieria.com	+52 33 2306 0598	General de Ley de Personas Morales	\N	\N	299	2026-07-07 13:28:02.267502-06	2026-07-07 16:36:54.366415-06	f	2026-07-07 16:36:54.368453-06	\N	\N	AV. VALLARTA 6503, PISO 10A, CIUDAD GRANJA	\N	\N	\N	ZAPOPAN	Jalisco	45010	Mexico	45010	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
sola	sola	\N	\N	\N	\N	\N	\N	371	2026-07-07 13:28:02.450563-06	2026-07-07 16:36:54.412842-06	f	2026-07-07 16:36:54.414459-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
SOLUCIONES POR ENCIMA DE TODO	SOLUCIONES POR ENCIMA DE TODO	\N	\N	+52 33 2833 9151	General de Ley de Personas Morales	\N	\N	303	2026-07-07 13:28:02.27567-06	2026-07-07 16:36:54.446075-06	f	2026-07-07 16:36:54.44757-06	\N	\N	PROLONGACION TEPEYAC 1201, BALCONES DEL SOL	\N	\N	\N	ZAPOPAN	Jalisco	45068	Mexico	45068	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
Structures & industrial Services	Structures & industrial Services	\N	proyectos.diametal@gmail.com	+52 449 537 2760	General de Ley de Personas Morales	\N	\N	327	2026-07-07 13:28:02.36267-06	2026-07-07 16:36:54.492537-06	f	2026-07-07 16:36:54.493878-06	\N	\N	Michoacán #213, Fracc. México.	\N	\N	\N	Aguascalientes	Aguascalientes	20270	Mexico	20270	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Aguascalientes
SURMAN POLANCO	SURMAN POLANCO	\N	\N	+52 871 707 8800 ext. 1003	General de Ley de Personas Morales	\N	\N	307	2026-07-07 13:28:02.319501-06	2026-07-07 16:36:54.513037-06	f	2026-07-07 16:36:54.514949-06	\N	\N	BLVD. RODRIGUEZ TRIANA 1882 , COL. LA MERCED	\N	\N	\N	TORREON	Coahuila	11560	Mexico	11560	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TORREON
TECNOCONTROL JALISCO	TECNOCONTROL JALISCO	\N	\N	\N	\N	\N	\N	331	2026-07-07 13:28:02.370416-06	2026-07-07 16:36:54.548994-06	f	2026-07-07 16:36:54.551334-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Tecnoglobal PH7, S.A. de C.V.	Tecnoglobal PH7, S.A. de C.V.	\N	jmartirez@tecnoglobal.mx	\N	General de Ley de Personas Morales	\N	\N	339	2026-07-07 13:28:02.388468-06	2026-07-07 16:36:54.588089-06	f	2026-07-07 16:36:54.589757-06	\N	\N	\N	\N	\N	\N	Zapopan	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
TOTAL FARMA MEXICO	TOTAL FARMA MEXICO	\N	serviciosgeneralesgdl@totalfarmamexico.mx	+52 33 1296 9751	General de Ley de Personas Morales	\N	\N	335	2026-07-07 13:28:02.379262-06	2026-07-07 16:36:54.653994-06	f	2026-07-07 16:36:54.656525-06	\N	\N	Volcán Popocatepetl #4581, El Coli Urbano 1er Sección	\N	\N	\N	Zapopan	Jalisco	45070	Mexico	45070	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Tuercas y Abrazaderas Ensa, S.A. de C.V.	Tuercas y Abrazaderas Ensa, S.A. de C.V.	\N	ventas@suspensionesensa.com	+52 33 3619 8679	General de Ley de Personas Morales	\N	\N	343	2026-07-07 13:28:02.396257-06	2026-07-07 16:36:57.569246-06	f	2026-07-07 16:36:57.571182-06	\N	\N	Clz Ejercito 789	\N	\N	\N	Guadalajara	Jalisco	44460	Mexico	44460	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Vamsa las Fuentes	Vamsa las Fuentes	\N	fernando.colmenares@nissanlasfuentes.mx	+52 33 1022 8781	General de Ley de Personas Morales	\N	\N	347	2026-07-07 13:28:02.404111-06	2026-07-07 16:36:57.623911-06	f	2026-07-07 16:36:57.625826-06	\N	\N	Avenida Lopez Mateos 6001	\N	\N	\N	Zapopan	Jalisco	45080	Mexico	45080	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Volkswagen del Centro	Volkswagen del Centro	\N	gustavo.vargas@vwdelcentro.com.mx	+52 449 182 0510	General de Ley de Personas Morales	\N	\N	351	2026-07-07 13:28:02.41176-06	2026-07-07 16:36:57.674581-06	f	2026-07-07 16:36:57.676796-06	\N	\N	Av Independencia 1863, Trojes de Alonso	\N	\N	\N	Aguascalientes	Aguascalientes	20116	Mexico	20116	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Aguascalientes
Wolfsburg de Occidente	Wolfsburg de Occidente	\N	sotelob777@gmail.com	+52 33 1990 0045	General de Ley de Personas Morales	\N	\N	355	2026-07-07 13:28:02.418794-06	2026-07-07 16:36:57.7216-06	f	2026-07-07 16:36:57.723145-06	\N	\N	Av. Lazaro Cardenas 2603-A Comercial Abastos	\N	\N	\N	Zapopan	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
ZURICH TEC DE MEXICO	ZURICH TEC DE MEXICO	\N	produccion@zurichtec.com.mx	+52 378 118 7914	General de Ley de Personas Morales	\N	\N	359	2026-07-07 13:28:02.426648-06	2026-07-07 16:36:57.790714-06	f	2026-07-07 16:36:57.792285-06	\N	\N	LAGO MAYOR #206 COL. TAMAULIPAS SECCION VIRGENCISTAS	\N	\N	\N	CIUDAD NEZAHUALCOYOTL	Ciudad de México	57300	Mexico	57300	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	CIUDAD NEZAHUALCOYOTL
generico	generico	\N	\N	+52 33 1308 7348	General de Ley de Personas Morales	\N	\N	364	2026-07-07 13:28:02.438009-06	2026-07-07 16:36:40.665789-06	f	2026-07-07 16:36:40.667818-06	\N	\N	Amado Nervo 2200, Torre Bio N6 Int. 601, Jardines del Sol	\N	\N	\N	Zapopan	Jalisco	45050	Mexico	45050	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
laboratorios DICA	laboratorios DICA	\N	laboratorio.dica@gmail.com	+52 33 3697 1010	General de Ley de Personas Morales	\N	\N	368	2026-07-07 13:28:02.445091-06	2026-07-07 16:36:47.893063-06	f	2026-07-07 16:36:47.894899-06	\N	\N	EL SALTO, JALISCO	\N	\N	\N	El salto	Jalisco	45694	Mexico	45694	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El salto
Ricardo Javier Trillo Villalobos	Ricardo Javier Trillo Villalobos	\N	rtrillov@imch.mx	+52 614 516 1125	General de Ley de Personas Morales	\N	\N	284	2026-07-07 13:28:02.239909-06	2026-07-07 16:36:51.24554-06	f	2026-07-07 16:36:51.247679-06	\N	\N	34 No. 3803, Col. Dale	\N	\N	\N	Chihuahua	Chihuahua	31050	Mexico	31050	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Chihuahua
Royal Gaskets & Joins	Royal Gaskets & Joins	\N	sandra_hevia@royalgnj.com	+52 593 914 2632	General de Ley de Personas Morales	\N	\N	288	2026-07-07 13:28:02.246994-06	2026-07-07 16:36:51.313383-06	f	2026-07-07 16:36:51.315725-06	\N	\N	Jose Martí, manzana 2 lote 16, Barrio San Francisco	\N	\N	\N	Coyotepec	Ciudad de México	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Coyotepec
Saleiko Industrial	Saleiko Industrial	\N	df.rodriguez@saleiko.com	+52 33 3033 7926	\N	\N	\N	308	2026-07-07 13:28:02.321773-06	2026-07-07 16:36:51.340152-06	f	2026-07-07 16:36:51.34212-06	\N	\N	Carretera a Zalamea Km. 3, Local 8	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
SANDRA CECILIA PRECIADO CAMPILLO	SANDRA CECILIA PRECIADO CAMPILLO	\N	\N	\N	General de Ley de Personas Morales	\N	\N	292	2026-07-07 13:28:02.254209-06	2026-07-07 16:36:54.111045-06	f	2026-07-07 16:36:54.114237-06	\N	\N	EL GRECO 561, COL. PRADOS DE PROVIDENCIA	\N	\N	\N	GUADALAJARA	Jalisco	44670	Mexico	44670	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Santiago Torres Flores	Santiago Torres Flores	\N	\N	+52 33 1092 1243	General de Ley de Personas Morales	\N	\N	312	2026-07-07 13:28:02.329954-06	2026-07-07 16:36:54.162585-06	f	2026-07-07 16:36:54.164428-06	\N	\N	Pedro Moreno 4	\N	\N	\N	Guadalajara	Jalisco	44985	Mexico	44985	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Schott de México, S.A. de C.V.	Schott de México, S.A. de C.V.	\N	fernanda.hernandez@schott.com	+52 271 716 6690 ext. 293	General de Ley de Personas Morales	\N	\N	316	2026-07-07 13:28:02.339798-06	2026-07-07 16:36:54.236442-06	f	2026-07-07 16:36:54.238019-06	\N	\N	Veracruz Ver MX, Carretera México - Veracruz Km. 349 S/N, Venta Parada	\N	\N	\N	Veracruz	Veracruz	94946	Mexico	94946	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Veracruz
SELMA DANIELA SANCHEZ ORTIZ	SELMA DANIELA SANCHEZ ORTIZ	\N	ventas@solpesa.com.mx	+52 33 3103 1723	General de Ley de Personas Morales	\N	\N	296	2026-07-07 13:28:02.261704-06	2026-07-07 16:36:54.247739-06	f	2026-07-07 16:36:54.249475-06	\N	\N	LOMA NORTE 8372, LOMA DORADA	\N	\N	\N	TONALA	Jalisco	45402	Mexico	45402	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TONALA
Servishell	Servishell	\N	abel.cruz@servishell.com	+52 33 3120 9795	General de Ley de Personas Morales	\N	\N	320	2026-07-07 13:28:02.348734-06	2026-07-07 16:36:54.300763-06	f	2026-07-07 16:36:54.30259-06	\N	\N	Victoriano Salado Alvarez #225, ladrón de guevara	\N	\N	\N	Guadalajara	Jalisco	44600	Mexico	44600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Sims Lifecycle Services	Sims Lifecycle Services	\N	\N	+52 56 1042 2569	\N	\N	\N	324	2026-07-07 13:28:02.357295-06	2026-07-07 16:36:54.353556-06	f	2026-07-07 16:36:54.355146-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
SIS COMEDORES	SIS COMEDORES	\N	ssyma@sisc-comedores.com	\N	General de Ley de Personas Morales	\N	\N	300	2026-07-07 13:28:02.269772-06	2026-07-07 16:36:54.377559-06	f	2026-07-07 16:36:54.379248-06	\N	\N	MARIANO OTERO 2509 DEL FRESNO 2DA SECCION GUADALAJARA	\N	\N	\N	GUADALAJARA	Jalisco	44900	Mexico	44900	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
SOPORTE ELECTRICO INTERNACIONAL	SOPORTE ELECTRICO INTERNACIONAL	\N	\N	+52 33 1604 9402	General de Ley de Personas Morales	\N	\N	304	2026-07-07 13:28:02.312592-06	2026-07-07 16:36:54.457413-06	f	2026-07-07 16:36:54.459224-06	\N	\N	JUAN PALOMAR Y ARIAS 439 INT. 101	\N	\N	\N	GUADALAJARA	Jalisco	44670	Mexico	44670	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Suministros y Sanidad RX	Suministros y Sanidad RX	\N	jainal.gil@gmail.com	+52 33 1910 3500	\N	\N	\N	328	2026-07-07 13:28:02.364325-06	2026-07-07 16:36:54.503461-06	f	2026-07-07 16:36:54.505009-06	\N	\N	Tepeyac 409, Int. P1	\N	\N	\N	Zapopan	\N	45040	Mexico	45040	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
TECNOCONTROL JALISCO, TECNOCONTROL JALISCO	TECNOCONTROL JALISCO, TECNOCONTROL JALISCO	\N	almacenjcompany@gmail.com	\N	\N	\N	\N	332	2026-07-07 13:28:02.372173-06	2026-07-07 16:36:54.562633-06	f	2026-07-07 16:36:54.5651-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Telecontroles de Guadalajara	Telecontroles de Guadalajara	\N	telecontrolesdegdl@gmail.com	+52 33 1557 3783	\N	\N	\N	340	2026-07-07 13:28:02.390804-06	2026-07-07 16:36:54.620816-06	f	2026-07-07 16:36:54.623392-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
TRANS & LOG HSA	TRANS & LOG HSA	\N	\N	+52 33 1668 6825	General de Ley de Personas Morales	\N	\N	336	2026-07-07 13:28:02.381446-06	2026-07-07 16:36:57.517937-06	f	2026-07-07 16:36:57.520372-06	\N	\N	AV. LOMAS VERDES 793, EL ORGANO	\N	\N	\N	SAN PEDRO TLAQUEPAQUE	Jalisco	45588	Mexico	45588	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	SAN PEDRO TLAQUEPAQUE
UNION GASTRONOMICA B Y S	UNION GASTRONOMICA B Y S	\N	\N	\N	General de Ley de Personas Morales	\N	\N	344	2026-07-07 13:28:02.398257-06	2026-07-07 16:36:57.582098-06	f	2026-07-07 16:36:57.584532-06	\N	\N	PINO 2176	\N	\N	\N	GUADALAJARA	Jalisco	44900	Mexico	44900	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Válvulas y Asesoría Integral en Termoplásticos, S.A. de C.V.	Válvulas y Asesoría Integral en Termoplásticos, S.A. de C.V.	\N	seguridad@vasitesa.com.mx	\N	General de Ley de Personas Morales	\N	\N	352	2026-07-07 13:28:02.413652-06	2026-07-07 16:36:57.61126-06	f	2026-07-07 16:36:57.613574-06	\N	\N	MERCURIO 34, COL ENSEUÑOS	\N	\N	\N	Cuautitlán Izcalli	Ciudad de México	54740	Mexico	54740	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Cuautitlán Izcalli
Vidara	Vidara	\N	kathia.rivera@vidara.com	+52 33 3777 4343	General de Ley de Personas Morales	\N	\N	348	2026-07-07 13:28:02.406118-06	2026-07-07 16:36:57.648508-06	f	2026-07-07 16:36:57.650779-06	\N	\N	Paseos del Valle 5211, Guadalajara Technology Park	\N	\N	\N	Zapopan	Jalisco	45019	Mexico	45019	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
volkswan galerias	volkswan galerias	\N	\N	\N	\N	\N	\N	372	2026-07-07 13:28:02.4523-06	2026-07-07 16:36:57.70095-06	f	2026-07-07 16:36:57.702783-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
YALIERCP	YALIERCP	\N	servicioyaliercp@hotmail.com	+52 33 3723 1524	General de Ley de Personas Morales	\N	\N	356	2026-07-07 13:28:02.4211-06	2026-07-07 16:36:57.744716-06	f	2026-07-07 16:36:57.746623-06	\N	\N	DEL FEDERALISMO NORTE 1651	\N	\N	\N	GUADALAJARA	Jalisco	44260	Mexico	44260	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Zar kruse	Zar kruse	\N	calidad_zarkruse@zar-kruse.com	+52 729 531 7213	General de Ley de Personas Morales	\N	\N	360	2026-07-07 13:28:02.428947-06	2026-07-07 16:36:57.765952-06	f	2026-07-07 16:36:57.768558-06	\N	\N	Av. Libertad y Blvd. Prot. Carlos Hank Gonzalez	\N	\N	\N	Santiago Tianguistenco	México	52600	Mexico	52600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Santiago Tianguistenco
Rogers Foam	Rogers Foam	\N	eelizabeth@rogersfoam.com	\N	General de Ley de Personas Morales	\N	\N	286	2026-07-07 13:28:02.243478-06	2026-07-07 16:36:51.273339-06	f	2026-07-07 16:36:51.275083-06	\N	\N	Tlaquepaque, 45598 San Pedro Tlaquepaque, Jal.	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45598	Mexico	45598	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
ABASTECEDORA DE INSUMOS PARA LA SALUD	ABASTECEDORA DE INSUMOS PARA LA SALUD	XAXX010101000	responsable.sanitario@abisalud.com	\N	General de Ley de Personas Morales	\N	\N	2	2026-07-07 13:28:01.519585-06	2026-07-07 16:36:32.153552-06	f	2026-07-07 16:36:32.156279-06	\N	\N	NORTE 31 A, NUEVA INDUSTRIAL VALLEJO	\N	\N	\N	GUSTAVO A MADERO	Ciudad de México	07700	Mexico	07700	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUSTAVO A MADERO
ARTURO DANIEL AMEZCUA MORA	ARTURO DANIEL AMEZCUA MORA	\N	k.navarro@censelab.com.mx	+52 33 3195 9884	General de Ley de Personas Morales	\N	\N	11	2026-07-07 13:28:01.563751-06	2026-07-07 16:36:32.361834-06	f	2026-07-07 16:36:32.364635-06	\N	\N	ANDRES QUINTANA ROO 2594, SANTA ELENA ALCALDE PONIENTE	\N	\N	\N	GUADALAJARA	Jalisco	44220	Mexico	44220	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Audi Center Galerias	Audi Center Galerias	\N	auxcalidad@audigalerias.com.mx	\N	General de Ley de Personas Morales	\N	\N	31	2026-07-07 13:28:01.637731-06	2026-07-07 16:36:32.464307-06	f	2026-07-07 16:36:32.466135-06	\N	\N	Av. Vallarta 5400-A Jardines Vallarta	\N	\N	\N	Zapopan	Jalisco	45110	Mexico	45110	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Audi center patria	Audi center patria	\N	fvalenzuela@audipatria.mx	+52 33 3648 5650	General de Ley de Personas Morales	\N	\N	32	2026-07-07 13:28:01.64213-06	2026-07-07 16:36:32.476539-06	f	2026-07-07 16:36:32.478596-06	\N	\N	Av. patria 2112 Col. Santa Isabel	\N	\N	\N	Zapopan	Jalisco	45110	Mexico	45110	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Automotriz celaya S.A. DE C.V.	Automotriz celaya S.A. DE C.V.	\N	\N	+52 442 594 9587	General de Ley de Personas Morales	\N	\N	33	2026-07-07 13:28:01.645887-06	2026-07-07 16:36:32.531535-06	f	2026-07-07 16:36:32.533725-06	\N	\N	Boulevard Adolfo Lopez Mateos # 1515	\N	\N	\N	Celaya	Guanajuato	38060	Mexico	38060	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Celaya
Begalat pharma	Begalat pharma	\N	\N	\N	General de Ley de Personas Morales	\N	\N	38	2026-07-07 13:28:01.662623-06	2026-07-07 16:36:32.581904-06	f	2026-07-07 16:36:32.584351-06	\N	\N	Calle 23	\N	\N	\N	Ciudad de Mexico	Ciudad de México	03800	Mexico	03800	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Ciudad de Mexico
BIODESARROLLOS VALMEX	BIODESARROLLOS VALMEX	\N	lmelendez@biovalmex.com	\N	General de Ley de Personas Morales	\N	\N	34	2026-07-07 13:28:01.649448-06	2026-07-07 16:36:32.624832-06	f	2026-07-07 16:36:32.626635-06	\N	\N	C CIRCUITO CRISANTEMOS 10, SANTA CRUZ DE LAS FLORES	\N	\N	\N	TLAJOMULCO DE ZUÑIGA	Jalisco	45640	Mexico	45640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAJOMULCO DE ZUÑIGA
cem	cem	\N	\N	\N	\N	\N	\N	362	2026-07-07 13:28:02.433076-06	2026-07-07 16:36:36.471045-06	f	2026-07-07 16:36:36.472871-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
henni	henni	\N	\N	\N	\N	\N	\N	366	2026-07-07 13:28:02.441955-06	2026-07-07 16:36:43.8256-06	f	2026-07-07 16:36:43.82702-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
SAMADHI LUCIA CARDENAS LIMON	SAMADHI LUCIA CARDENAS LIMON	\N	laboratorio@grupojolokev.com	\N	General de Ley de Personas Morales	\N	\N	290	2026-07-07 13:28:02.250308-06	2026-07-07 16:36:51.368178-06	f	2026-07-07 16:36:51.369941-06	\N	\N	HUASTECOS 292, ZAPOTALITO	\N	\N	\N	ARANDAS	Jalisco	47180	Mexico	47180	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ARANDAS
Sandvik Mining and Construction de México, S.A. de C.V., Monica cisneros	Sandvik Mining and Construction de México, S.A. de C.V., Monica cisneros	\N	monica.cisneros@sandvik.com	\N	General de Ley de Personas Morales	\N	\N	310	2026-07-07 13:28:02.326543-06	2026-07-07 16:36:54.137302-06	f	2026-07-07 16:36:54.13888-06	\N	\N	Benjamin Franklin Mz. 10 Lt. 8	\N	\N	\N	Tlajomulco de Zúñiga	Jalisco	45640	Mexico	45640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlajomulco de Zúñiga
SAUL ISAAC ARCE CORTES	SAUL ISAAC ARCE CORTES	\N	saul.cortes@mycmetrology.com.mx	\N	\N	\N	\N	294	2026-07-07 13:28:02.258157-06	2026-07-07 16:36:54.182815-06	f	2026-07-07 16:36:54.184579-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Sazón Natural	Sazón Natural	\N	calidad@sazonnatural.com	+52 33 1199 4765	General de Ley de Personas Morales	\N	\N	314	2026-07-07 13:28:02.334618-06	2026-07-07 16:36:54.204676-06	f	2026-07-07 16:36:54.206663-06	\N	\N	Av. San Miguel 399, Interior San Eduardo 86	\N	\N	\N	Zapopan	Jalisco	45019	Mexico	45019	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
scho	scho	\N	\N	\N	\N	\N	\N	370	2026-07-07 13:28:02.448519-06	2026-07-07 16:36:54.225818-06	f	2026-07-07 16:36:54.227144-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Servicios Enga Ingenieria S.C.	Servicios Enga Ingenieria S.C.	\N	enga_ing@hotmail.com	+52 33 3440 2163	General de Ley de Personas Morales	\N	\N	318	2026-07-07 13:28:02.344309-06	2026-07-07 16:36:54.267987-06	f	2026-07-07 16:36:54.269804-06	\N	\N	AVE SAN MIGUEL #399 COL. SAN JUAN DE OCOTAN	\N	\N	\N	ZAPOPAN	Jalisco	45019	Mexico	45019	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZAPOPAN
Sherex México	Sherex México	\N	compras@sherexmx.com	+52 442 196 8075	General de Ley de Personas Morales	\N	\N	322	2026-07-07 13:28:02.352786-06	2026-07-07 16:36:54.322302-06	f	2026-07-07 16:36:54.323689-06	\N	\N	Circuito Balvanera S.A bodega II,	\N	\N	\N	Corregidora	Querétaro	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Corregidora
SIALICO FOOD SAFETY	SIALICO FOOD SAFETY	\N	hugo@sialico.com	\N	General de Ley de Personas Morales	\N	\N	298	2026-07-07 13:28:02.265363-06	2026-07-07 16:36:54.342386-06	f	2026-07-07 16:36:54.343803-06	\N	\N	Lateral Via Altixcayotl 5210, int. F1	\N	\N	\N	San Andres Cholula	Puebla	72820	Mexico	72820	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Andres Cholula
Sistemas Electricos Industriales y Comerciales	Sistemas Electricos Industriales y Comerciales	\N	francisco.moraramirez@hotmail.com	+52 33 1948 3918	General de Ley de Personas Morales	\N	\N	326	2026-07-07 13:28:02.360743-06	2026-07-07 16:36:54.401369-06	f	2026-07-07 16:36:54.403565-06	\N	\N	Calle San Flipe No. 1138, Santa Teresita	\N	\N	\N	Guadalajara	Jalisco	44200	Mexico	44200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
SOLUCIONES INTELIGENTES SIHRO	SOLUCIONES INTELIGENTES SIHRO	\N	reinaldo.mtz@solucionessihro.com	+52 771 116 5056	General de Ley de Personas Morales	\N	\N	302	2026-07-07 13:28:02.273915-06	2026-07-07 16:36:54.434529-06	f	2026-07-07 16:36:54.436531-06	\N	\N	CERRADA DE TULIPANES #3, LA RANCHERIA	\N	\N	\N	PROGRESO DE OBREGON	Hidalgo	42730	Mexico	42730	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	PROGRESO DE OBREGON
STEEL MASTER STRUCTURES MX	STEEL MASTER STRUCTURES MX	\N	ndelalama@steelmaster.com.mx	+52 33 1672 4723	General de Ley de Personas Morales	\N	\N	306	2026-07-07 13:28:02.317222-06	2026-07-07 16:36:54.479615-06	f	2026-07-07 16:36:54.48224-06	\N	\N	LOMA ZACAPU #481, LOMA DORADA	\N	\N	\N	TONALA	Jalisco	45402	Mexico	45402	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TONALA
TECHNOLOGY & STEEL	TECHNOLOGY & STEEL	\N	calidad2@technologysteel.com	+52 33 1076 6913	General de Ley de Personas Morales	\N	\N	330	2026-07-07 13:28:02.368245-06	2026-07-07 16:36:54.525463-06	f	2026-07-07 16:36:54.527373-06	\N	\N	TALAMANTES #406 PISO 4TO, SAN MARCOS	\N	\N	\N	AGUASCALIENTES	Aguascalientes	20070	Mexico	20070	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	AGUASCALIENTES
Tecnoglobal	Tecnoglobal	\N	\N	+52 33 4777 0030	General de Ley de Personas Morales	\N	\N	338	2026-07-07 13:28:02.386359-06	2026-07-07 16:36:54.575625-06	f	2026-07-07 16:36:54.577397-06	\N	\N	Av. Del Tigre #2140,	\N	\N	\N	Zapopan	Jalisco	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
TOP HEALTH	TOP HEALTH	\N	metrologo1@top-health.mx	\N	\N	\N	\N	334	2026-07-07 13:28:02.376982-06	2026-07-07 16:36:54.639584-06	f	2026-07-07 16:36:54.641912-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Tubos y Aceros Maquinados	Tubos y Aceros Maquinados	\N	maria.reyes@f-tam.com	+52 33 3796 0510	General de Ley de Personas Morales	\N	\N	342	2026-07-07 13:28:02.394229-06	2026-07-07 16:36:57.553249-06	f	2026-07-07 16:36:57.557743-06	\N	\N	Colima 105	\N	\N	\N	Santa Cruz de las Flores	Jalisco	45640	Mexico	45640	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Santa Cruz de las Flores
Volkswagen Galerias	Volkswagen Galerias	\N	\N	\N	\N	\N	\N	350	2026-07-07 13:28:02.410128-06	2026-07-07 16:36:57.687696-06	f	2026-07-07 16:36:57.689872-06	\N	\N	\N	\N	\N	\N	\N	\N	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	\N
Wasion, S. de R.L. de C.V.	Wasion, S. de R.L. de C.V.	\N	teresita.cabrera@wasion.com	+52 472 690 8060	General de Ley de Personas Morales	\N	\N	354	2026-07-07 13:28:02.416929-06	2026-07-07 16:36:57.710751-06	f	2026-07-07 16:36:57.712255-06	\N	\N	Av. Mina de Guadalupe No. 930	\N	\N	\N	Silao de la Victoria	Guanajuato	36275	Mexico	36275	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Silao de la Victoria
ZF Suspensión Technology Guadalajara, S.A. de C.V.	ZF Suspensión Technology Guadalajara, S.A. de C.V.	\N	Juan.Palacios@zf.com	\N	General de Ley de Personas Morales	\N	\N	358	2026-07-07 13:28:02.425077-06	2026-07-07 16:36:57.77916-06	f	2026-07-07 16:36:57.781047-06	\N	\N	Carretera El Salto - La Capilla Km. 3.5	\N	\N	\N	El Salto	Jalisco	45680	Mexico	45680	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El Salto
BMC Medical Manufacturing	BMC Medical Manufacturing	\N	marian.rodriguez@bmcmm.com	+52 81 1022 0042	General de Ley de Personas Morales	\N	\N	35	2026-07-07 13:28:01.653692-06	2026-07-07 16:36:32.637213-06	f	2026-07-07 16:36:32.638873-06	\N	\N	Blvd. TLC 5010-2, Parque industrial Milenium.	\N	\N	\N	Apodaca	Nuevo León	\N	Mexico	\N	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Apodaca
CA&CER Ingeniería y Metrología S.A.S	CA&CER Ingeniería y Metrología S.A.S	\N	administracion@caycer.com.mx	3 3260 16 58	General de Ley de Personas Morales	\N	\N	41	2026-07-07 13:28:01.673308-06	2026-07-07 16:36:32.669814-06	f	2026-07-07 16:36:32.671393-06	\N	\N	Calle Batalla de Puebla N° 3643-D, El Tapatío	\N	\N	\N	Tlaquepaque	Jalisco	45588	Mexico	45588	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Tlaquepaque
CALIBRACIONES E INSTRUMENTOS	CALIBRACIONES E INSTRUMENTOS	\N	ventas@calinsto.com	+52 33 2379 8099	General de Ley de Personas Morales	\N	\N	44	2026-07-07 13:28:01.68445-06	2026-07-07 16:36:32.719541-06	f	2026-07-07 16:36:32.721513-06	\N	\N	Calle Brillante #1576 Col. Mariano Otero	\N	\N	\N	Zapopan	Jalisco	45067	Mexico	45067	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
CRG PROYECTOS Y MANTENIMIENTO INDUSTRIAL DE LOS ALTOS	CRG PROYECTOS Y MANTENIMIENTO INDUSTRIAL DE LOS ALTOS	\N	admonfin.pmi25@gmail.com	+52 378 102 7707	General de Ley de Personas Morales	\N	\N	64	2026-07-07 13:28:01.741903-06	2026-07-07 16:36:36.834088-06	f	2026-07-07 16:36:36.836199-06	\N	\N	AVENIDA SANTA CRUZ #152, SANTA CRUZ DEL VALLE	\N	\N	\N	TLAJOMULCO DE ZUÑIGA	Jalisco	45655	Mexico	45655	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TLAJOMULCO DE ZUÑIGA
DISTRIBUIDORA DE EQUIPO MEDICO INDSUTRIAL DE MÉXICO	DISTRIBUIDORA DE EQUIPO MEDICO INDSUTRIAL DE MÉXICO	\N	javier.gonzalez@demim.com.mx	+52 33 1616 3463	General de Ley de Personas Morales	\N	\N	91	2026-07-07 13:28:01.819135-06	2026-07-07 16:36:36.884571-06	f	2026-07-07 16:36:36.886274-06	\N	\N	CARR LEON-LAGOS #251 LOC.13	\N	\N	\N	LEON	Guanajuato	37669	Mexico	37669	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	LEON
Distribuidora Volkswagen Central, S.A. de C.V.	Distribuidora Volkswagen Central, S.A. de C.V.	\N	\N	+52 449 352 5398	General de Ley de Personas Morales	\N	\N	94	2026-07-07 13:28:01.827542-06	2026-07-07 16:36:36.893214-06	f	2026-07-07 16:36:36.894768-06	\N	\N	Jose Maria Chavez 1321, Fracc. Jardines de la Asuncion	\N	\N	\N	Aguascalientes	Aguascalientes	20270	Mexico	20270	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Aguascalientes
FGR PROYECTOS INTEGRALES & INDUSTRIALES S.A DE C. V.	FGR PROYECTOS INTEGRALES & INDUSTRIALES S.A DE C. V.	\N	arturo.gonzalez@fpi-isa.com	+52 229 227 7952	General de Ley de Personas Morales	\N	\N	113	2026-07-07 13:28:01.87619-06	2026-07-07 16:36:40.400089-06	f	2026-07-07 16:36:40.402494-06	\N	\N	DESTILERIA 1800	\N	\N	\N	TEQUILA	Jalisco	46400	Mexico	46400	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	TEQUILA
Grupo Castaniel, S. de R.L. de C.V.	Grupo Castaniel, S. de R.L. de C.V.	\N	\N	+52 922 112 0121	General de Ley de Personas Morales	\N	\N	145	2026-07-07 13:28:01.953959-06	2026-07-07 16:36:40.745609-06	f	2026-07-07 16:36:40.747688-06	\N	\N	Rio San Francisco #163, Int #63, Col. Colegio del Aire	\N	\N	\N	Zapopan	Jalisco	45200	Mexico	45200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Grupo Excala	Grupo Excala	\N	daniela.moreno@grupoexcala.com	+57 313 7671627	Sin obligaciones fiscales	\N	\N	147	2026-07-07 13:28:01.958443-06	2026-07-07 16:36:40.788061-06	f	2026-07-07 16:36:40.790472-06	\N	\N	Av. Juan Gil Preciado 1904 Naves 5 y 6 Modulo 10, Los Robles,	\N	\N	\N	Zapopan	Jalisco	45134	Mexico	45134	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Hector Alejandro Ovalle Rendon	Hector Alejandro Ovalle Rendon	\N	\N	\N	General de Ley de Personas Morales	\N	\N	156	2026-07-07 13:28:01.977213-06	2026-07-07 16:36:43.78805-06	f	2026-07-07 16:36:43.790377-06	\N	\N	Cooperativa 21 de agosto 347	\N	\N	\N	Mazatlan	Sinaloa	82020	Mexico	82020	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Mazatlan
Hidromóvil, S.A. de C.V.	Hidromóvil, S.A. de C.V.	\N	compras@hidromovil.com	\N	General de Ley de Personas Morales	\N	\N	159	2026-07-07 13:28:01.983905-06	2026-07-07 16:36:43.859513-06	f	2026-07-07 16:36:43.86108-06	\N	\N	Blvd. Los Charros No. 1690	\N	\N	\N	Zapopan	Jalisco	45150	Mexico	45150	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Hospital Santa Margarita, S.A. de C.V.	Hospital Santa Margarita, S.A. de C.V.	\N	jefaturadelaboratorio@hsmgdl.com	\N	General de Ley de Personas Morales	\N	\N	162	2026-07-07 13:28:01.990749-06	2026-07-07 16:36:43.90614-06	f	2026-07-07 16:36:43.907668-06	\N	\N	Garibaldi No. 880	\N	\N	\N	Guadalajara	Jalisco	44200	Mexico	44200	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Instalaciones y Mantenimiento de Calidad, S.A. de C.V.	Instalaciones y Mantenimiento de Calidad, S.A. de C.V.	\N	Javier.gomez@servicioshvac.com	+52 33 2005 0170	General de Ley de Personas Morales	\N	\N	184	2026-07-07 13:28:02.036413-06	2026-07-07 16:36:44.136143-06	f	2026-07-07 16:36:44.138003-06	\N	\N	Periférico Sur No. 7215 Local 6	\N	\N	\N	San Pedro Tlaquepaque	Jalisco	45610	Mexico	45610	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Pedro Tlaquepaque
Laboratorio Santo Domingo	Laboratorio Santo Domingo	\N	\N	+52 462 191 5019	General de Ley de Personas Morales	\N	\N	210	2026-07-07 13:28:02.088568-06	2026-07-07 16:36:47.86726-06	f	2026-07-07 16:36:47.869683-06	\N	\N	Fernando Aranguren 840 Col. Belenes	\N	\N	\N	Zapopan	Jalisco	45150	Mexico	45150	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Zapopan
Laminados Extruidos Plásticos, S.A. de C.V.	Laminados Extruidos Plásticos, S.A. de C.V.	\N	metrologialmx@laminex.com.mx	+52 33 3837 1750	General de Ley de Personas Morales	\N	\N	213	2026-07-07 13:28:02.09485-06	2026-07-07 16:36:47.918875-06	f	2026-07-07 16:36:47.920655-06	\N	\N	Av. Cañas No. 3686	\N	\N	\N	Guadalajara	Jalisco	44470	Mexico	44470	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Guadalajara
Madrigal Navarro, Francisco Saúl	Madrigal Navarro, Francisco Saúl	\N	compras@grupomad.mx	+52 33 1423 7359	General de Ley de Personas Morales	\N	\N	227	2026-07-07 13:28:02.121653-06	2026-07-07 16:36:48.05463-06	f	2026-07-07 16:36:48.056679-06	\N	\N	Jose Maria Morelos #29	\N	\N	\N	El Salto	Jalisco	45694	Mexico	45694	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El Salto
METROLOGIA Y SERVICIOS MYC	METROLOGIA Y SERVICIOS MYC	MSM180712686	\N	\N	Régimen General de Ley Personas Morales	\N	\N	1	2026-07-07 13:28:01.44382-06	2026-07-07 16:36:48.205502-06	f	2026-07-07 16:36:48.206882-06	\N	\N	AV. CRISTOBAL COLON	6086	57	VILLA DE SANTA MARIA	SAN PEDRO TLAQUEPAQUE	JALISCO	45601	Mexico	45601	Csf_MSM180712686.pdf	clientes/cliente_1/constancia_fiscal_5e0f2c597a334762a7786187765d3477.pdf	2026-07-07 14:33:36.71498-06	persona_moral	\N	\N	\N	\N	CALLE	TLAQUEPAQUE	SAN PEDRO TLAQUEPAQUE
MOLEX DE MEXICO GUADALAJARA 2, S DE RL DE CV	MOLEX DE MEXICO GUADALAJARA 2, S DE RL DE CV	\N	ivan.garcia@molex.com	+52 33 4166 0021	General de Ley de Personas Morales	\N	\N	222	2026-07-07 13:28:02.110965-06	2026-07-07 16:36:48.324126-06	f	2026-07-07 16:36:48.326277-06	\N	\N	AVENIDA GUADALAJARA 1 CENTRO LOGISTICO JALISCO II	\N	\N	\N	ZACOALCO DE TORRES JALISCO	Jalisco	45777	Mexico	45777	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	ZACOALCO DE TORRES JALISCO
OPERADORA QUÍMICA MENLUN S.A.  DE C.V.	OPERADORA QUÍMICA MENLUN S.A.  DE C.V.	\N	guadalupe.luna@pmpsquimicos.com	+52 55 7261 8988 ext. 111	General de Ley de Personas Morales	\N	\N	255	2026-07-07 13:28:02.182764-06	2026-07-07 16:36:50.968982-06	f	2026-07-07 16:36:50.970918-06	\N	\N	Ejidos de Cuautitlan Manzana 46 lote 7 Lazaro Cardenas	\N	\N	\N	Cuautitlan	Ciudad de México	54800	Mexico	54800	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	Cuautitlan
Peiyuan Automobile Parts Manufacture, S.A. de C.V.	Peiyuan Automobile Parts Manufacture, S.A. de C.V.	\N	guadalupe.flores@peiyuan.com.mx	+52 33 4737 5240	General de Ley de Personas Morales	\N	\N	272	2026-07-07 13:28:02.216638-06	2026-07-07 16:36:51.081512-06	f	2026-07-07 16:36:51.083225-06	\N	\N	Camino al Pino No. 26	\N	\N	\N	El Salto	Jalisco	45680	Mexico	45680	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	El Salto
VAQCSA GUADALAJARA	VAQCSA GUADALAJARA	\N	ivan.villarreal@seat-guadalajara.com.mx	+52 33 1406 7246	General de Ley de Personas Morales	\N	\N	346	2026-07-07 13:28:02.402015-06	2026-07-07 16:36:57.635882-06	f	2026-07-07 16:36:57.63758-06	\N	\N	AV. AMERICAS #599, LADRON DE GUEVARA	\N	\N	\N	GUADALAJARA	Jalisco	44600	Mexico	44600	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	GUADALAJARA
Voit Automotive de México	Voit Automotive de México	\N	Irving.Tinajero@arbomex.mx	+52 33 1607 3873	General de Ley de Personas Morales	\N	\N	349	2026-07-07 13:28:02.408026-06	2026-07-07 16:36:57.661045-06	f	2026-07-07 16:36:57.663041-06	\N	\N	km12 Carretera Guadalajara,	\N	\N	\N	San Jose del Castillo	Jalisco	45680	Mexico	45680	\N	\N	\N	persona_moral	\N	\N	\N	\N	\N	\N	San Jose del Castillo
\.


--
-- Data for Name: controlled_document_versions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.controlled_document_versions (document_id, revision, file_path, original_filename, mime_type, checksum, change_summary, uploaded_by_id, approved_by_id, reviewed_by_id, status, effective_date, uploaded_at, approved_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: controlled_documents; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.controlled_documents (code, name, document_type, quality_level, current_revision, issue_date, last_review_date, effective_date, retention_time, digital_location, status, description, created_by_id, id, created_at, updated_at) FROM stdin;
MDG-01	Manual de Gestion de la Calidad	manual	Nivel I	\N	\N	\N	\N	\N	\N	draft	Documento semilla del nucleo documental.	\N	1	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
FCA-02	Lista Maestra de Documentos	record	Nivel II	\N	\N	\N	\N	\N	\N	draft	Lista maestra inicial.	\N	2	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
PMP-01	Procedimiento de uso y calibracion de manometros y vacuometros	procedure	Nivel II	\N	\N	\N	\N	\N	\N	draft	Procedimiento base para presion.	\N	3	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
FCA-15-7	Calibracion de manometros	field_sheet_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de hoja de campo.	\N	4	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
FPV-01	Orden de trabajo	work_order_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de orden de trabajo.	\N	5	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
FCA-22	Cotizacion	quotation_template	Nivel III	\N	\N	\N	\N	\N	\N	draft	Formato semilla de cotizacion.	\N	6	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
FCA-18-1	Calculo de incertidumbre	uncertainty_calculation	Nivel III	\N	\N	\N	\N	\N	\N	draft	Fuente documental para modelo de incertidumbre futuro.	\N	7	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
\.


--
-- Data for Name: credit_notes; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.credit_notes (invoice_id, folio, issued_on, reason, subtotal, tax_total, total, status, observations, created_by_id, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: document_interpretations; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.document_interpretations (document_id, document_version_id, name, interpretation_type, magnitude, equipment_type, service_type, calibration_scope, data, status, version, created_by_id, approved_by_id, approved_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: document_templates; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.document_templates (template_key, name, company_name, company_tagline, company_rfc, company_email, company_website, company_address, company_phone, document_title, document_subtitle, document_code, document_revision, document_issued_on, terms_version, commercial_terms, metrological_terms, legal_terms, privacy_notice, acceptance_text, show_summary_terms, show_full_terms, show_acceptance_signature, is_active, id, created_at, updated_at) FROM stdin;
quotation	Plantilla de cotizacion MYC	Metrologia y Servicios MYC	Servicios de metrologia, calibracion, venta y soporte tecnico especializado.	MYC000000XXX	contacto@mycmetrology.com.mx	www.mycmetrology.com.mx			COTIZACION	Propuesta comercial de servicios, calibracion y soluciones tecnicas	FCA-23-2	\N	2025-03-28	V1	Precios expresados en moneda nacional, salvo indicacion contraria.\nVigencia sujeta a la fecha indicada en esta cotizacion.\nTiempos de entrega y alcance final se confirman al recibir autorizacion.	Los servicios metrologicos se ejecutan conforme al alcance tecnico autorizado y a la disponibilidad de patrones aplicables.	La autorizacion de esta cotizacion implica aceptacion de las condiciones comerciales, tecnicas y documentales descritas.	Los datos del cliente se usan exclusivamente para fines comerciales, operativos, documentales y de facturacion relacionados con el servicio solicitado.	Acepto las condiciones comerciales, metrologicas y legales de la presente cotizacion.	t	t	t	t	1	2026-07-07 14:37:04.04706-06	2026-07-07 14:37:04.04706-06
\.


--
-- Data for Name: equipment; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.equipment (service_order_id, service_order_item_id, status, name, brand, model, serial_number, internal_id, range_or_capacity, initial_condition, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, calibration_scope) FROM stdin;
\.


--
-- Data for Name: field_sheet_reference_standards; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_reference_standards (field_sheet_id, reference_standard_id, usage_role, measurement_section, notes, id, created_at, updated_at, reference_standard_certificate_id, selected_uncertainty_id, selection_status, selection_notes, validation_snapshot) FROM stdin;
\.


--
-- Data for Name: field_sheet_results; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_results (field_sheet_id, section_key, row_number, pattern_value, ibc_value_1, ibc_value_2, ibc_value_3, unit, notes, id, created_at, updated_at, row_data) FROM stdin;
\.


--
-- Data for Name: field_sheet_template_definitions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheet_template_definitions (template_key, name, description, status, version, definition_json, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
general	Hoja de Campo General	\N	active	1	{"id": null, "source": "fallback", "template_key": "general", "key": "general", "name": "Hoja de Campo General", "description": null, "type": "general", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	1	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
temperatura	Hoja de Campo Temperatura	\N	active	1	{"id": null, "source": "fallback", "template_key": "temperatura", "key": "temperatura", "name": "Hoja de Campo Temperatura", "description": null, "type": "temperatura", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	2	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
termometro	Hoja de Campo Termómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "termometro", "key": "termometro", "name": "Hoja de Campo Term\\u00f3metro", "description": null, "type": "termometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	3	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
termohigrometro	Hoja de Campo Termohigrómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "termohigrometro", "key": "termohigrometro", "name": "Hoja de Campo Termohigr\\u00f3metro", "description": null, "type": "termohigrometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	4	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
transductor_presion	Hoja de Campo Transductor de Presión	\N	active	1	{"id": null, "source": "fallback", "template_key": "transductor_presion", "key": "transductor_presion", "name": "Hoja de Campo Transductor de Presi\\u00f3n", "description": null, "type": "transductor_presion", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "pressure", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "pressure_4", "block_type": "PressureTableBlock", "title": "Tabla de presi\\u00f3n", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "pressure_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "pressure_4", "title": "Tabla de presi\\u00f3n", "rows": 8, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	9	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
cronometro	Hoja de Campo Cronómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "cronometro", "key": "cronometro", "name": "Hoja de Campo Cron\\u00f3metro", "description": null, "type": "cronometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	5	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
tacometro	Hoja de Campo Tacómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "tacometro", "key": "tacometro", "name": "Hoja de Campo Tac\\u00f3metro", "description": null, "type": "tacometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "direct_comparison", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "simple_comparison_4", "block_type": "SimpleComparisonTableBlock", "title": "Tabla comparativa", "visible_fields": [], "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "simple_comparison_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "simple_comparison_4", "title": "Tabla comparativa", "rows": 10, "columns": [{"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": "18%", "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	6	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
anemometro	Hoja de Campo Anemómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "anemometro", "key": "anemometro", "name": "Hoja de Campo Anem\\u00f3metro", "description": null, "type": "anemometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_anemometer_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	7	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
manometro	Hoja de Campo Manómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "manometro", "key": "manometro", "name": "Hoja de Campo Man\\u00f3metro", "description": null, "type": "manometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "pressure", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "pressure_4", "block_type": "PressureTableBlock", "title": "Tabla de presi\\u00f3n", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "pressure_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "pressure_4", "title": "Tabla de presi\\u00f3n", "rows": 8, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	8	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
valvula	Hoja de Campo Válvula	\N	active	1	{"id": null, "source": "fallback", "template_key": "valvula", "key": "valvula", "name": "Hoja de Campo V\\u00e1lvula", "description": null, "type": "valvula", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "pressure", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "pressure_4", "block_type": "PressureTableBlock", "title": "Tabla de presi\\u00f3n", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "pressure_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "pressure_4", "title": "Tabla de presi\\u00f3n", "rows": 8, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "ascending_pattern", "label": "Ascendente patr\\u00f3n", "source": "ascending_pattern", "width": null, "unit": null, "editable": true}, {"key": "ascending_instrument", "label": "Ascendente instrumento", "source": "ascending_instrument", "width": null, "unit": null, "editable": true}, {"key": "descending_pattern", "label": "Descendente patr\\u00f3n", "source": "descending_pattern", "width": null, "unit": null, "editable": true}, {"key": "descending_instrument", "label": "Descendente instrumento", "source": "descending_instrument", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	10	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
dimensional	Hoja de Campo Dimensional	\N	active	1	{"id": null, "source": "fallback", "template_key": "dimensional", "key": "dimensional", "name": "Hoja de Campo Dimensional", "description": null, "type": "dimensional", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	11	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
regla	Hoja de Campo Regla	\N	active	1	{"id": null, "source": "fallback", "template_key": "regla", "key": "regla", "name": "Hoja de Campo Regla", "description": null, "type": "regla", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	12	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
vernier	Hoja de Campo Vernier	\N	active	1	{"id": null, "source": "fallback", "template_key": "vernier", "key": "vernier", "name": "Hoja de Campo Vernier", "description": null, "type": "vernier", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	13	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
luxometro	Hoja de Campo Luxómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "luxometro", "key": "luxometro", "name": "Hoja de Campo Lux\\u00f3metro", "description": null, "type": "luxometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	22	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
micrometro	Hoja de Campo Micrómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "micrometro", "key": "micrometro", "name": "Hoja de Campo Micr\\u00f3metro", "description": null, "type": "micrometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	14	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
flexometro	Hoja de Campo Flexómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "flexometro", "key": "flexometro", "name": "Hoja de Campo Flex\\u00f3metro", "description": null, "type": "flexometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "dimensional", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "dimensional_4", "block_type": "DimensionalTableBlock", "title": "Tabla dimensional", "visible_fields": [], "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "dimensional_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "dimensional_4", "title": "Tabla dimensional", "rows": 10, "columns": [{"key": "nominal_length", "label": "Longitud nominal", "source": "nominal_length", "width": null, "unit": null, "editable": true}, {"key": "pattern_reading", "label": "Lectura patr\\u00f3n", "source": "pattern_reading", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Lectura instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	15	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
masa	Hoja de Campo Masa	\N	active	1	{"id": null, "source": "fallback", "template_key": "masa", "key": "masa", "name": "Hoja de Campo Masa", "description": null, "type": "masa", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	16	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
balanza	Hoja de Campo Balanza	\N	active	1	{"id": null, "source": "fallback", "template_key": "balanza", "key": "balanza", "name": "Hoja de Campo Balanza", "description": null, "type": "balanza", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	17	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
bascula	Hoja de Campo Báscula	\N	active	1	{"id": null, "source": "fallback", "template_key": "bascula", "key": "bascula", "name": "Hoja de Campo B\\u00e1scula", "description": null, "type": "bascula", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	18	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
peso_patron	Hoja de Campo Peso Patrón	\N	active	1	{"id": null, "source": "fallback", "template_key": "peso_patron", "key": "peso_patron", "name": "Hoja de Campo Peso Patr\\u00f3n", "description": null, "type": "peso_patron", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "mass", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "mass_balance_4", "block_type": "MassBalanceTableBlock", "title": "Tabla masa / balanza", "visible_fields": [], "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 8, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "mass_balance_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "mass_balance_4", "title": "Tabla masa / balanza", "rows": 8, "columns": [{"key": "applied_load", "label": "Carga aplicada", "source": "applied_load", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "eccentricity_value", "label": "Excentricidad", "source": "eccentricity_value", "width": null, "unit": null, "editable": true}, {"key": "repeatability_value", "label": "Repetibilidad", "source": "repeatability_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	19	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
electrica	Hoja de Campo Eléctrica	\N	active	1	{"id": null, "source": "fallback", "template_key": "electrica", "key": "electrica", "name": "Hoja de Campo El\\u00e9ctrica", "description": null, "type": "electrica", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 2, "pdf_template": "field_sheet_electrical_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "electrical", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "electrical_4", "block_type": "ElectricalTableBlock", "title": "Tabla el\\u00e9ctrica", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "electrical_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "sectioned_5", "block_type": "SectionedTableBlock", "title": "Secciones personalizadas", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "sectioned_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	20	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
multimetro	Hoja de Campo Multímetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "multimetro", "key": "multimetro", "name": "Hoja de Campo Mult\\u00edmetro", "description": null, "type": "multimetro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "electrical", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "electrical_4", "block_type": "ElectricalTableBlock", "title": "Tabla el\\u00e9ctrica", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "electrical_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "sectioned_5", "block_type": "SectionedTableBlock", "title": "Secciones personalizadas", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [{"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "sectioned_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "voltage_ac", "title": "Voltaje AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "voltage_dc", "title": "Voltaje DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_ac", "title": "Corriente AC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "current_dc", "title": "Corriente DC", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "resistance", "title": "Resistencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "frequency", "title": "Frecuencia", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "continuity", "title": "Continuidad", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "custom_section", "title": "Secci\\u00f3n personalizada", "rows": 5, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	21	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
sonido	Hoja de Campo Sonido	\N	active	1	{"id": null, "source": "fallback", "template_key": "sonido", "key": "sonido", "name": "Hoja de Campo Sonido", "description": null, "type": "sonido", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	23	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
sonometro	Hoja de Campo Sonómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "sonometro", "key": "sonometro", "name": "Hoja de Campo Son\\u00f3metro", "description": null, "type": "sonometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	24	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
torquimetro	Hoja de Campo Torquímetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "torquimetro", "key": "torquimetro", "name": "Hoja de Campo Torqu\\u00edmetro", "description": null, "type": "torquimetro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	25	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
dinamometro	Hoja de Campo Dinamómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "dinamometro", "key": "dinamometro", "name": "Hoja de Campo Dinam\\u00f3metro", "description": null, "type": "dinamometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	26	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
durometro	Hoja de Campo Durómetro	\N	active	1	{"id": null, "source": "fallback", "template_key": "durometro", "key": "durometro", "name": "Hoja de Campo Dur\\u00f3metro", "description": null, "type": "durometro", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_5", "block_key": "ObservationsBlock_5", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 5, "capture_order": 5, "order": 5, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_6", "block_key": "SignaturesBlock_6", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	27	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
volumen	Hoja de Campo Volumen	\N	active	1	{"id": null, "source": "fallback", "template_key": "volumen", "key": "volumen", "name": "Hoja de Campo Volumen", "description": null, "type": "volumen", "status": "active", "version": 1, "is_active": true, "code": "FCA-30", "revision": "R1", "pages": 1, "pdf_template": "field_sheet_general_pdf.html", "document_code": "FCA-30", "document_revision": "R1", "table_family": "multipoint", "blocks": [{"title": "Datos generales", "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address"], "fields": [], "required": true, "key": "GeneralDataBlock_1", "block_key": "GeneralDataBlock_1", "block_type": "GeneralDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 1, "capture_order": 1, "order": 1, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Datos del equipo", "visible_fields": ["equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division"], "fields": [], "required": true, "key": "EquipmentDataBlock_2", "block_key": "EquipmentDataBlock_2", "block_type": "EquipmentDataBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 2, "capture_order": 2, "order": 2, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Condiciones ambientales", "visible_fields": ["reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end"], "fields": [], "required": false, "key": "EnvironmentalBlock_3", "block_key": "EnvironmentalBlock_3", "block_type": "EnvironmentalBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 3, "capture_order": 3, "order": 3, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"key": "multi_point_4", "block_type": "MultiPointTableBlock", "title": "Tabla multipunto", "visible_fields": [], "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 10, "min_rows": 3, "max_rows": 20, "allow_add_rows": true, "required": true, "print_order": 4, "capture_order": 4, "order": 4, "block_key": "multi_point_4", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"key": "repeatability_5", "block_type": "RepeatabilityTableBlock", "title": "Tabla de repetibilidad", "visible_fields": [], "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}], "sections": [], "suggested_unit": null, "rows": 5, "min_rows": 3, "max_rows": 10, "allow_add_rows": true, "required": true, "print_order": 5, "capture_order": 5, "order": 5, "block_key": "repeatability_5", "visible": true, "table_config": {}, "allow_remove_rows": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}, "fields": []}, {"title": "Datos t\\u00e9cnicos", "visible_fields": ["initial_condition", "final_condition", "method", "units", "observations", "evidence_notes"], "fields": [], "required": true, "key": "ObservationsBlock_6", "block_key": "ObservationsBlock_6", "block_type": "ObservationsBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 6, "capture_order": 6, "order": 6, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}, {"title": "Firmas", "visible_fields": ["calibrated_by", "reviewed_by", "report_made_by"], "fields": [], "required": true, "key": "SignaturesBlock_7", "block_key": "SignaturesBlock_7", "block_type": "SignaturesBlock", "columns": [], "sections": [], "table_config": {}, "suggested_unit": null, "rows": null, "min_rows": null, "max_rows": null, "allow_add_rows": false, "allow_remove_rows": false, "print_order": 7, "capture_order": 7, "order": 7, "visible": true, "print_visible": true, "capture_visible": true, "pdf_visible": true, "metadata": {}}], "validations": {}, "print_config": {}, "pdf_config": {}, "permissions_config": {}, "metadata": {}, "visible_fields": ["work_order_number", "reserved_certificate_folio", "attention", "company", "address", "equipment", "brand", "model", "serial_number", "internal_id", "location", "minimum_division", "reception_date", "calibration_date", "next_calibration_date", "environment_humidity_start", "environment_humidity_end", "environment_temperature_start", "environment_temperature_end", "initial_condition", "final_condition", "method", "units", "observations", "evidence_notes", "calibrated_by", "reviewed_by", "report_made_by"], "result_sections": [{"key": "multi_point_4", "title": "Tabla multipunto", "rows": 10, "columns": [{"key": "nominal_point", "label": "Punto nominal", "source": "nominal_point", "width": null, "unit": null, "editable": true}, {"key": "pattern_value", "label": "Patr\\u00f3n", "source": "pattern_value", "width": null, "unit": null, "editable": true}, {"key": "instrument_reading", "label": "Indicaci\\u00f3n instrumento", "source": "instrument_reading", "width": null, "unit": null, "editable": true}, {"key": "error_value", "label": "Error", "source": "error_value", "width": null, "unit": null, "editable": true}, {"key": "result_value", "label": "Resultado", "source": "result_value", "width": null, "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}, {"key": "repeatability_5", "title": "Tabla de repetibilidad", "rows": 5, "columns": [{"key": "point_label", "label": "Punto", "source": "point_label", "width": null, "unit": null, "editable": true}, {"key": "reading_1", "label": "Lectura 1", "source": "reading_1", "width": null, "unit": null, "editable": true}, {"key": "reading_2", "label": "Lectura 2", "source": "reading_2", "width": null, "unit": null, "editable": true}, {"key": "reading_3", "label": "Lectura 3", "source": "reading_3", "width": null, "unit": null, "editable": true}, {"key": "average_value", "label": "Promedio", "source": "average_value", "width": null, "unit": null, "editable": true}, {"key": "unit", "label": "Unidad", "source": "unit", "width": "12%", "unit": null, "editable": true}, {"key": "notes", "label": "Observaciones", "source": "notes", "width": "18%", "unit": null, "editable": true}]}]}	28	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
\.


--
-- Data for Name: field_sheets; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.field_sheets (equipment_id, status, initial_condition, final_condition, pattern_used, results, observations, evidence_notes, method, environmental_conditions, technician_notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, template_key, work_order_number, calibration_place, reception_date, calibration_date, next_calibration_date, environment_humidity_start, environment_humidity_end, environment_temperature_start, environment_temperature_end, equipment_general_condition, consider_equipment_deviations, units, calibrated_by, reviewed_by, report_made_by, purchase_order_or_quotation, calibration_procedure_id, returned_to_technician_at, returned_to_technician_by_id, returned_to_technician_reason, certificate_client_mode, certificate_client_company, certificate_client_attention, certificate_client_address, apply_certificate_client_to_order, minimum_division, location, attention, company, address, template_definition_json, template_definition_version) FROM stdin;
\.


--
-- Data for Name: invoice_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoice_items (invoice_id, quotation_item_id, certificate_id, equipment_id, description, quantity, unit, sat_unit, sat_key, unit_price, discount_total, tax_rate, tax_total, line_total, notes, service_type, source_type, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invoice_payments; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoice_payments (invoice_id, paid_on, amount, bank_name, bank_account, reference, payment_method, payment_form, status, notes, registered_by_id, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invoice_settings; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoice_settings (key, default_series, next_sequence, reset_annually, default_tax_rate, default_currency, default_credit_days, allow_manual_folio, forms_of_payment, methods_of_payment, usage_cfdi_catalog, tax_regime_catalog, currency_catalog, sat_product_keys, sat_units, banks, bank_accounts, legal_texts, billing_emails, emitter_data, pdf_template_name, cfdi_future_parameters, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.invoices (internal_uuid, series, folio, client_id, fiscal_client_id, service_order_id, quotation_id, issued_on, due_on, subtotal, tax_total, withholding_total, discount_total, total, balance_due, amount_paid, status, payment_method, payment_form, usage_cfdi, currency, credit_days, observations, internal_comments, cancellation_reason, created_by_id, updated_by_id, last_payment_on, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: quotation_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.quotation_items (quotation_id, service_name, description, quantity, unit_price, total, id, created_at, updated_at, is_active, deleted_at, deleted_by, catalog_item_id, unit, currency, commodity, calibration_scope, quotation_legend, sat_key, sat_unit, internal_unit, discount_percent, tax_object, tax_rate, tax_total) FROM stdin;
\.


--
-- Data for Name: quotations; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.quotations (folio, client_id, status, issued_on, valid_until, subtotal, tax_total, total, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, advisor_id) FROM stdin;
\.


--
-- Data for Name: reference_standard_certificate_uncertainties; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standard_certificate_uncertainties (certificate_id, magnitude, measurement_type, range_min, range_max, unit, uncertainty_value, uncertainty_unit, k_factor, confidence_level, distribution, formula_reference, notes, is_active, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reference_standard_certificates; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standard_certificates (reference_standard_id, controlled_document_id, controlled_document_version_id, certificate_number, issuing_laboratory, accreditation_body, accreditation_number, calibration_date, expiration_date, received_date, status, is_current, traceability_statement, environmental_conditions, notes, created_by_id, approved_by_id, approved_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reference_standard_uncertainties; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standard_uncertainties (reference_standard_id, range_min, range_max, unit, uncertainty_value, coverage_factor_k, distribution, notes, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reference_standards; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.reference_standards (internal_code, name, description, owner_company, magnitude, brand, model, serial_number, identification, unit, range_min, range_max, resolution, coverage_factor_k, provider, calibration_laboratory, certificate_number, certificate_file_path, calibrated_on, next_calibration_on, status, notes, is_active, deleted_at, deleted_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.roles (name, description, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
Administrador	Acceso total al sistema.	1	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
Comercial	Gestion comercial, clientes y cotizaciones.	2	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
Tecnico	Gestion tecnica de equipos y hojas de campo.	3	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
Captura	Captura y generacion documental.	4	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
Calidad	Revision y aprobacion de certificados.	5	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
Finanzas	Pagos, facturacion y liberacion financiera.	6	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
Cliente	Acceso limitado para cliente externo.	7	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06	t	\N	\N
Desarrollador	Acceso tecnico avanzado para desarrollo y soporte.	8	2026-07-07 13:27:43.740202-06	2026-07-07 13:27:43.740202-06	t	\N	\N
\.


--
-- Data for Name: service_order_items; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.service_order_items (service_order_id, quotation_item_id, service_name, quantity, status, id, created_at, updated_at, is_active, deleted_at, deleted_by, calibration_scope) FROM stdin;
\.


--
-- Data for Name: service_orders; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.service_orders (folio, client_id, quotation_id, status, agenda_date, closed_at, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by, advisor_id, technician_id, service_date, total_equipment, completed_equipment, requires_payment, work_order_number) FROM stdin;
\.


--
-- Data for Name: technical_profile_allowed_patterns; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.technical_profile_allowed_patterns (technical_profile_id, pattern_id, pattern_code, min_range, max_range, unit, priority, is_preferred, notes, created_at, id) FROM stdin;
\.


--
-- Data for Name: technical_profiles; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.technical_profiles (code, name, magnitude, equipment_type, service_type, calibration_scope, procedure_document_id, procedure_interpretation_id, field_sheet_template_document_id, certificate_template_document_id, uncertainty_source_document_id, status, version, rules, notes, created_by_id, approved_by_id, approved_at, id, created_at, updated_at) FROM stdin;
PT-PRESION-MANOMETRO-ACR-001	Perfil Tecnico Presion - Manometros Acreditado	Presion	Manometro	calibration	accredited	\N	\N	\N	\N	\N	draft	1	\N	Perfil semilla; no contiene calculos metrologicos.	\N	\N	\N	1	2026-07-07 13:27:20.638474-06	2026-07-07 13:27:20.638474-06
\.


--
-- Data for Name: uncertainty_calculations; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_calculations (field_sheet_id, uncertainty_model_id, status, calculated_at, calculation_snapshot, input_snapshot, component_results, formula_results, warnings, errors, id, created_at, updated_at, uncertainty_model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_components; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_components (model_id, key, name, description, source_type, distribution, divisor, sensitivity_coefficient, value_expression, required, sort_order, metadata_json, id, created_at, updated_at, is_active, deleted_at, deleted_by, model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_formulas; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_formulas (model_id, key, name, expression, result_key, description, sort_order, is_active_formula, id, created_at, updated_at, model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_model_exceptions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_model_exceptions (base_model_id, alternate_model_id, magnitude, equipment_type, equipment_model, procedure_id, profile_key, reason, authorized_by_id, authorized_at, status, id, created_at, updated_at, is_active, deleted_at, deleted_by, base_model_version_id, alternate_model_version_id) FROM stdin;
\.


--
-- Data for Name: uncertainty_model_versions; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_model_versions (model_id, version_number, status, change_summary, default_coverage_factor, submitted_at, submitted_by_id, approved_at, approved_by_id, obsolete_at, archived_at, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
\.


--
-- Data for Name: uncertainty_models; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.uncertainty_models (code, name, description, magnitude, equipment_family, version, status, default_coverage_factor, notes, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.user_roles (user_id, role_id) FROM stdin;
1	1
2	1
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: saulcortes
--

COPY public.users (email, full_name, hashed_password, role_id, id, created_at, updated_at, is_active, deleted_at, deleted_by) FROM stdin;
saul@myc.com	admin	$pbkdf2-sha256$29000$f8/Z2ztHKKVUKgXAOKeUEg$RdeV1LF/Le7jJ2HezvKwNmtkPUC.8L4SxCW6dBZfpeY	1	1	2026-07-07 13:27:43.740202-06	2026-07-07 13:27:43.740202-06	t	\N	\N
monse@myc.com	monse cortes	$pbkdf2-sha256$29000$/j.HsBYCoFSKMcb4n9Pa2w$OEOocyqE.W91YFkSjWTTFO4lQZbW814pE2PerYF0IoU	1	2	2026-07-07 14:15:51.978436-06	2026-07-07 14:27:55.164792-06	f	\N	\N
\.


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 754, true);


--
-- Name: calibration_procedures_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.calibration_procedures_id_seq', 1, false);


--
-- Name: catalog_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.catalog_items_id_seq', 1, false);


--
-- Name: certificates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.certificates_id_seq', 1, false);


--
-- Name: client_contacts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.client_contacts_id_seq', 94, true);


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.clients_id_seq', 372, true);


--
-- Name: controlled_document_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.controlled_document_versions_id_seq', 1, false);


--
-- Name: controlled_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.controlled_documents_id_seq', 7, true);


--
-- Name: credit_notes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.credit_notes_id_seq', 1, false);


--
-- Name: document_interpretations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.document_interpretations_id_seq', 1, false);


--
-- Name: document_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.document_templates_id_seq', 1, true);


--
-- Name: equipment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.equipment_id_seq', 1, false);


--
-- Name: field_sheet_reference_standards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_reference_standards_id_seq', 1, false);


--
-- Name: field_sheet_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_results_id_seq', 1, false);


--
-- Name: field_sheet_template_definitions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheet_template_definitions_id_seq', 28, true);


--
-- Name: field_sheets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.field_sheets_id_seq', 1, false);


--
-- Name: invoice_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoice_items_id_seq', 1, false);


--
-- Name: invoice_payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoice_payments_id_seq', 1, false);


--
-- Name: invoice_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoice_settings_id_seq', 1, false);


--
-- Name: invoices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.invoices_id_seq', 1, false);


--
-- Name: quotation_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.quotation_items_id_seq', 1, false);


--
-- Name: quotations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.quotations_id_seq', 1, false);


--
-- Name: reference_standard_certificate_uncertainties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standard_certificate_uncertainties_id_seq', 1, false);


--
-- Name: reference_standard_certificates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standard_certificates_id_seq', 1, false);


--
-- Name: reference_standard_uncertainties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standard_uncertainties_id_seq', 1, false);


--
-- Name: reference_standards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.reference_standards_id_seq', 1, false);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.roles_id_seq', 8, true);


--
-- Name: service_order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.service_order_items_id_seq', 1, false);


--
-- Name: service_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.service_orders_id_seq', 1, false);


--
-- Name: technical_profile_allowed_patterns_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.technical_profile_allowed_patterns_id_seq', 1, false);


--
-- Name: technical_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.technical_profiles_id_seq', 1, true);


--
-- Name: uncertainty_calculations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_calculations_id_seq', 1, false);


--
-- Name: uncertainty_components_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_components_id_seq', 1, false);


--
-- Name: uncertainty_formulas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_formulas_id_seq', 1, false);


--
-- Name: uncertainty_model_exceptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_model_exceptions_id_seq', 1, false);


--
-- Name: uncertainty_model_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_model_versions_id_seq', 1, false);


--
-- Name: uncertainty_models_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.uncertainty_models_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: saulcortes
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: calibration_procedures calibration_procedures_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures
    ADD CONSTRAINT calibration_procedures_pkey PRIMARY KEY (id);


--
-- Name: catalog_items catalog_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.catalog_items
    ADD CONSTRAINT catalog_items_pkey PRIMARY KEY (id);


--
-- Name: certificates certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_pkey PRIMARY KEY (id);


--
-- Name: client_contacts client_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.client_contacts
    ADD CONSTRAINT client_contacts_pkey PRIMARY KEY (id);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


--
-- Name: controlled_document_versions controlled_document_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_pkey PRIMARY KEY (id);


--
-- Name: controlled_documents controlled_documents_code_key; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents
    ADD CONSTRAINT controlled_documents_code_key UNIQUE (code);


--
-- Name: controlled_documents controlled_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents
    ADD CONSTRAINT controlled_documents_pkey PRIMARY KEY (id);


--
-- Name: credit_notes credit_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes
    ADD CONSTRAINT credit_notes_pkey PRIMARY KEY (id);


--
-- Name: document_interpretations document_interpretations_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_pkey PRIMARY KEY (id);


--
-- Name: document_templates document_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_templates
    ADD CONSTRAINT document_templates_pkey PRIMARY KEY (id);


--
-- Name: document_templates document_templates_template_key_key; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_templates
    ADD CONSTRAINT document_templates_template_key_key UNIQUE (template_key);


--
-- Name: equipment equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_pkey PRIMARY KEY (id);


--
-- Name: field_sheet_reference_standards field_sheet_reference_standards_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT field_sheet_reference_standards_pkey PRIMARY KEY (id);


--
-- Name: field_sheet_results field_sheet_results_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results
    ADD CONSTRAINT field_sheet_results_pkey PRIMARY KEY (id);


--
-- Name: field_sheet_template_definitions field_sheet_template_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_template_definitions
    ADD CONSTRAINT field_sheet_template_definitions_pkey PRIMARY KEY (id);


--
-- Name: field_sheets field_sheets_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT field_sheets_pkey PRIMARY KEY (id);


--
-- Name: invoice_items invoice_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_pkey PRIMARY KEY (id);


--
-- Name: invoice_payments invoice_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments
    ADD CONSTRAINT invoice_payments_pkey PRIMARY KEY (id);


--
-- Name: invoice_settings invoice_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_settings
    ADD CONSTRAINT invoice_settings_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: quotation_items quotation_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_pkey PRIMARY KEY (id);


--
-- Name: quotations quotations_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_pkey PRIMARY KEY (id);


--
-- Name: reference_standard_certificate_uncertainties reference_standard_certificate_uncertainties_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificate_uncertainties
    ADD CONSTRAINT reference_standard_certificate_uncertainties_pkey PRIMARY KEY (id);


--
-- Name: reference_standard_certificates reference_standard_certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_pkey PRIMARY KEY (id);


--
-- Name: reference_standard_uncertainties reference_standard_uncertainties_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_uncertainties
    ADD CONSTRAINT reference_standard_uncertainties_pkey PRIMARY KEY (id);


--
-- Name: reference_standards reference_standards_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standards
    ADD CONSTRAINT reference_standards_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: service_order_items service_order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items
    ADD CONSTRAINT service_order_items_pkey PRIMARY KEY (id);


--
-- Name: service_orders service_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT service_orders_pkey PRIMARY KEY (id);


--
-- Name: technical_profile_allowed_patterns technical_profile_allowed_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns
    ADD CONSTRAINT technical_profile_allowed_patterns_pkey PRIMARY KEY (id);


--
-- Name: technical_profiles technical_profiles_code_key; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_code_key UNIQUE (code);


--
-- Name: technical_profiles technical_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_calculations uncertainty_calculations_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT uncertainty_calculations_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_components uncertainty_components_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components
    ADD CONSTRAINT uncertainty_components_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_formulas uncertainty_formulas_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas
    ADD CONSTRAINT uncertainty_formulas_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_pkey PRIMARY KEY (id);


--
-- Name: uncertainty_models uncertainty_models_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_models
    ADD CONSTRAINT uncertainty_models_pkey PRIMARY KEY (id);


--
-- Name: field_sheet_reference_standards uq_field_sheet_reference_standard_usage; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT uq_field_sheet_reference_standard_usage UNIQUE (field_sheet_id, reference_standard_id, usage_role, measurement_section);


--
-- Name: field_sheet_results uq_field_sheet_results_row; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results
    ADD CONSTRAINT uq_field_sheet_results_row UNIQUE (field_sheet_id, section_key, row_number);


--
-- Name: field_sheet_template_definitions uq_field_sheet_template_key_version; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_template_definitions
    ADD CONSTRAINT uq_field_sheet_template_key_version UNIQUE (template_key, version);


--
-- Name: uncertainty_model_versions uq_uncertainty_model_versions_number; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uq_uncertainty_model_versions_number UNIQUE (model_id, version_number);


--
-- Name: uncertainty_models uq_uncertainty_models_code_version; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_models
    ADD CONSTRAINT uq_uncertainty_models_code_version UNIQUE (code, version);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_entity; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_entity ON public.audit_logs USING btree (entity);


--
-- Name: ix_audit_logs_entity_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_entity_id ON public.audit_logs USING btree (entity_id);


--
-- Name: ix_audit_logs_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_id ON public.audit_logs USING btree (id);


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_calibration_procedures_certificate_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_certificate_type ON public.calibration_procedures USING btree (certificate_type);


--
-- Name: ix_calibration_procedures_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_code ON public.calibration_procedures USING btree (code);


--
-- Name: ix_calibration_procedures_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_id ON public.calibration_procedures USING btree (id);


--
-- Name: ix_calibration_procedures_issuer_company; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_issuer_company ON public.calibration_procedures USING btree (issuer_company);


--
-- Name: ix_calibration_procedures_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_magnitude ON public.calibration_procedures USING btree (magnitude);


--
-- Name: ix_calibration_procedures_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_name ON public.calibration_procedures USING btree (name);


--
-- Name: ix_calibration_procedures_profile_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_profile_key ON public.calibration_procedures USING btree (profile_key);


--
-- Name: ix_calibration_procedures_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_status ON public.calibration_procedures USING btree (status);


--
-- Name: ix_calibration_procedures_uncertainty_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_uncertainty_model_id ON public.calibration_procedures USING btree (uncertainty_model_id);


--
-- Name: ix_calibration_procedures_uncertainty_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_uncertainty_model_version_id ON public.calibration_procedures USING btree (uncertainty_model_version_id);


--
-- Name: ix_calibration_procedures_version; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_calibration_procedures_version ON public.calibration_procedures USING btree (version);


--
-- Name: ix_catalog_items_category; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_category ON public.catalog_items USING btree (category);


--
-- Name: ix_catalog_items_commodity; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_commodity ON public.catalog_items USING btree (commodity);


--
-- Name: ix_catalog_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_id ON public.catalog_items USING btree (id);


--
-- Name: ix_catalog_items_internal_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_internal_key ON public.catalog_items USING btree (internal_key);


--
-- Name: ix_catalog_items_is_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_is_active ON public.catalog_items USING btree (is_active);


--
-- Name: ix_catalog_items_item_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_item_type ON public.catalog_items USING btree (item_type);


--
-- Name: ix_catalog_items_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_name ON public.catalog_items USING btree (name);


--
-- Name: ix_catalog_items_origin_currency; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_origin_currency ON public.catalog_items USING btree (origin_currency);


--
-- Name: ix_catalog_items_tax_object; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_catalog_items_tax_object ON public.catalog_items USING btree (tax_object);


--
-- Name: ix_certificates_authenticated_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_authenticated_by_id ON public.certificates USING btree (authenticated_by_id);


--
-- Name: ix_certificates_authentication_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_certificates_authentication_code ON public.certificates USING btree (authentication_code);


--
-- Name: ix_certificates_authentication_hash; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_authentication_hash ON public.certificates USING btree (authentication_hash);


--
-- Name: ix_certificates_capture_started_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_capture_started_by_id ON public.certificates USING btree (capture_started_by_id);


--
-- Name: ix_certificates_certificate_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_certificate_type ON public.certificates USING btree (certificate_type);


--
-- Name: ix_certificates_client_visible; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_client_visible ON public.certificates USING btree (client_visible);


--
-- Name: ix_certificates_equipment_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_equipment_id ON public.certificates USING btree (equipment_id);


--
-- Name: ix_certificates_expected_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_certificates_expected_folio ON public.certificates USING btree (expected_folio);


--
-- Name: ix_certificates_external_source; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_external_source ON public.certificates USING btree (external_source);


--
-- Name: ix_certificates_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_field_sheet_id ON public.certificates USING btree (field_sheet_id);


--
-- Name: ix_certificates_final_pdf_uploaded_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_final_pdf_uploaded_by_id ON public.certificates USING btree (final_pdf_uploaded_by_id);


--
-- Name: ix_certificates_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_certificates_folio ON public.certificates USING btree (folio);


--
-- Name: ix_certificates_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_id ON public.certificates USING btree (id);


--
-- Name: ix_certificates_match_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_match_status ON public.certificates USING btree (match_status);


--
-- Name: ix_certificates_quality_reviewed_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_quality_reviewed_by_id ON public.certificates USING btree (quality_reviewed_by_id);


--
-- Name: ix_certificates_released_to_client_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_released_to_client_by_id ON public.certificates USING btree (released_to_client_by_id);


--
-- Name: ix_certificates_sent_to_quality_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_sent_to_quality_by_id ON public.certificates USING btree (sent_to_quality_by_id);


--
-- Name: ix_certificates_service_order_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_service_order_id ON public.certificates USING btree (service_order_id);


--
-- Name: ix_certificates_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_certificates_status ON public.certificates USING btree (status);


--
-- Name: ix_client_contacts_client_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_client_contacts_client_id ON public.client_contacts USING btree (client_id);


--
-- Name: ix_client_contacts_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_client_contacts_id ON public.client_contacts USING btree (id);


--
-- Name: ix_clients_client_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_client_type ON public.clients USING btree (client_type);


--
-- Name: ix_clients_commercial_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_commercial_name ON public.clients USING btree (commercial_name);


--
-- Name: ix_clients_curp; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_curp ON public.clients USING btree (curp);


--
-- Name: ix_clients_email; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_email ON public.clients USING btree (email);


--
-- Name: ix_clients_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_id ON public.clients USING btree (id);


--
-- Name: ix_clients_legal_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_legal_name ON public.clients USING btree (legal_name);


--
-- Name: ix_clients_rfc; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_clients_rfc ON public.clients USING btree (rfc);


--
-- Name: ix_controlled_document_versions_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_approved_by_id ON public.controlled_document_versions USING btree (approved_by_id);


--
-- Name: ix_controlled_document_versions_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_document_id ON public.controlled_document_versions USING btree (document_id);


--
-- Name: ix_controlled_document_versions_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_id ON public.controlled_document_versions USING btree (id);


--
-- Name: ix_controlled_document_versions_reviewed_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_reviewed_by_id ON public.controlled_document_versions USING btree (reviewed_by_id);


--
-- Name: ix_controlled_document_versions_revision; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_revision ON public.controlled_document_versions USING btree (revision);


--
-- Name: ix_controlled_document_versions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_status ON public.controlled_document_versions USING btree (status);


--
-- Name: ix_controlled_document_versions_uploaded_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_document_versions_uploaded_by_id ON public.controlled_document_versions USING btree (uploaded_by_id);


--
-- Name: ix_controlled_documents_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_controlled_documents_code ON public.controlled_documents USING btree (code);


--
-- Name: ix_controlled_documents_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_created_by_id ON public.controlled_documents USING btree (created_by_id);


--
-- Name: ix_controlled_documents_document_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_document_type ON public.controlled_documents USING btree (document_type);


--
-- Name: ix_controlled_documents_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_id ON public.controlled_documents USING btree (id);


--
-- Name: ix_controlled_documents_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_name ON public.controlled_documents USING btree (name);


--
-- Name: ix_controlled_documents_quality_level; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_quality_level ON public.controlled_documents USING btree (quality_level);


--
-- Name: ix_controlled_documents_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_controlled_documents_status ON public.controlled_documents USING btree (status);


--
-- Name: ix_credit_notes_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_credit_notes_folio ON public.credit_notes USING btree (folio);


--
-- Name: ix_credit_notes_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_credit_notes_id ON public.credit_notes USING btree (id);


--
-- Name: ix_credit_notes_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_credit_notes_status ON public.credit_notes USING btree (status);


--
-- Name: ix_document_interpretations_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_approved_by_id ON public.document_interpretations USING btree (approved_by_id);


--
-- Name: ix_document_interpretations_calibration_scope; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_calibration_scope ON public.document_interpretations USING btree (calibration_scope);


--
-- Name: ix_document_interpretations_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_created_by_id ON public.document_interpretations USING btree (created_by_id);


--
-- Name: ix_document_interpretations_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_document_id ON public.document_interpretations USING btree (document_id);


--
-- Name: ix_document_interpretations_document_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_document_version_id ON public.document_interpretations USING btree (document_version_id);


--
-- Name: ix_document_interpretations_equipment_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_equipment_type ON public.document_interpretations USING btree (equipment_type);


--
-- Name: ix_document_interpretations_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_id ON public.document_interpretations USING btree (id);


--
-- Name: ix_document_interpretations_interpretation_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_interpretation_type ON public.document_interpretations USING btree (interpretation_type);


--
-- Name: ix_document_interpretations_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_magnitude ON public.document_interpretations USING btree (magnitude);


--
-- Name: ix_document_interpretations_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_name ON public.document_interpretations USING btree (name);


--
-- Name: ix_document_interpretations_service_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_service_type ON public.document_interpretations USING btree (service_type);


--
-- Name: ix_document_interpretations_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_interpretations_status ON public.document_interpretations USING btree (status);


--
-- Name: ix_document_templates_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_document_templates_id ON public.document_templates USING btree (id);


--
-- Name: ix_document_templates_template_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_document_templates_template_key ON public.document_templates USING btree (template_key);


--
-- Name: ix_equipment_calibration_scope; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_calibration_scope ON public.equipment USING btree (calibration_scope);


--
-- Name: ix_equipment_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_id ON public.equipment USING btree (id);


--
-- Name: ix_equipment_internal_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_internal_id ON public.equipment USING btree (internal_id);


--
-- Name: ix_equipment_serial_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_serial_number ON public.equipment USING btree (serial_number);


--
-- Name: ix_equipment_service_order_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_service_order_id ON public.equipment USING btree (service_order_id);


--
-- Name: ix_equipment_service_order_item_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_service_order_item_id ON public.equipment USING btree (service_order_item_id);


--
-- Name: ix_equipment_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_equipment_status ON public.equipment USING btree (status);


--
-- Name: ix_field_sheet_reference_standards_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_field_sheet_id ON public.field_sheet_reference_standards USING btree (field_sheet_id);


--
-- Name: ix_field_sheet_reference_standards_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_id ON public.field_sheet_reference_standards USING btree (id);


--
-- Name: ix_field_sheet_reference_standards_reference_standard_c_5cb4; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_reference_standard_c_5cb4 ON public.field_sheet_reference_standards USING btree (reference_standard_certificate_id);


--
-- Name: ix_field_sheet_reference_standards_reference_standard_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_reference_standard_id ON public.field_sheet_reference_standards USING btree (reference_standard_id);


--
-- Name: ix_field_sheet_reference_standards_selected_uncertainty_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_reference_standards_selected_uncertainty_id ON public.field_sheet_reference_standards USING btree (selected_uncertainty_id);


--
-- Name: ix_field_sheet_results_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_results_field_sheet_id ON public.field_sheet_results USING btree (field_sheet_id);


--
-- Name: ix_field_sheet_results_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_results_id ON public.field_sheet_results USING btree (id);


--
-- Name: ix_field_sheet_results_section_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_results_section_key ON public.field_sheet_results USING btree (section_key);


--
-- Name: ix_field_sheet_template_definitions_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_template_definitions_id ON public.field_sheet_template_definitions USING btree (id);


--
-- Name: ix_field_sheet_template_definitions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_template_definitions_status ON public.field_sheet_template_definitions USING btree (status);


--
-- Name: ix_field_sheet_template_definitions_template_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheet_template_definitions_template_key ON public.field_sheet_template_definitions USING btree (template_key);


--
-- Name: ix_field_sheets_calibration_procedure_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_calibration_procedure_id ON public.field_sheets USING btree (calibration_procedure_id);


--
-- Name: ix_field_sheets_equipment_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_equipment_id ON public.field_sheets USING btree (equipment_id);


--
-- Name: ix_field_sheets_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_id ON public.field_sheets USING btree (id);


--
-- Name: ix_field_sheets_returned_to_technician_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_returned_to_technician_by_id ON public.field_sheets USING btree (returned_to_technician_by_id);


--
-- Name: ix_field_sheets_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_status ON public.field_sheets USING btree (status);


--
-- Name: ix_field_sheets_template_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_template_key ON public.field_sheets USING btree (template_key);


--
-- Name: ix_field_sheets_work_order_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_field_sheets_work_order_number ON public.field_sheets USING btree (work_order_number);


--
-- Name: ix_invoice_items_certificate_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_certificate_id ON public.invoice_items USING btree (certificate_id);


--
-- Name: ix_invoice_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_id ON public.invoice_items USING btree (id);


--
-- Name: ix_invoice_items_invoice_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_invoice_id ON public.invoice_items USING btree (invoice_id);


--
-- Name: ix_invoice_items_source_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_items_source_type ON public.invoice_items USING btree (source_type);


--
-- Name: ix_invoice_payments_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_id ON public.invoice_payments USING btree (id);


--
-- Name: ix_invoice_payments_invoice_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_invoice_id ON public.invoice_payments USING btree (invoice_id);


--
-- Name: ix_invoice_payments_reference; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_reference ON public.invoice_payments USING btree (reference);


--
-- Name: ix_invoice_payments_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_payments_status ON public.invoice_payments USING btree (status);


--
-- Name: ix_invoice_settings_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoice_settings_id ON public.invoice_settings USING btree (id);


--
-- Name: ix_invoice_settings_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_invoice_settings_key ON public.invoice_settings USING btree (key);


--
-- Name: ix_invoices_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_invoices_folio ON public.invoices USING btree (folio);


--
-- Name: ix_invoices_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoices_id ON public.invoices USING btree (id);


--
-- Name: ix_invoices_internal_uuid; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_invoices_internal_uuid ON public.invoices USING btree (internal_uuid);


--
-- Name: ix_invoices_series; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoices_series ON public.invoices USING btree (series);


--
-- Name: ix_invoices_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_invoices_status ON public.invoices USING btree (status);


--
-- Name: ix_quotation_items_catalog_item_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotation_items_catalog_item_id ON public.quotation_items USING btree (catalog_item_id);


--
-- Name: ix_quotation_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotation_items_id ON public.quotation_items USING btree (id);


--
-- Name: ix_quotation_items_quotation_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotation_items_quotation_id ON public.quotation_items USING btree (quotation_id);


--
-- Name: ix_quotations_advisor_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_advisor_id ON public.quotations USING btree (advisor_id);


--
-- Name: ix_quotations_client_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_client_id ON public.quotations USING btree (client_id);


--
-- Name: ix_quotations_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_quotations_folio ON public.quotations USING btree (folio);


--
-- Name: ix_quotations_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_id ON public.quotations USING btree (id);


--
-- Name: ix_quotations_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_quotations_status ON public.quotations USING btree (status);


--
-- Name: ix_reference_standard_certificate_uncertainties_certificate_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_certificate_id ON public.reference_standard_certificate_uncertainties USING btree (certificate_id);


--
-- Name: ix_reference_standard_certificate_uncertainties_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_id ON public.reference_standard_certificate_uncertainties USING btree (id);


--
-- Name: ix_reference_standard_certificate_uncertainties_is_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_is_active ON public.reference_standard_certificate_uncertainties USING btree (is_active);


--
-- Name: ix_reference_standard_certificate_uncertainties_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_magnitude ON public.reference_standard_certificate_uncertainties USING btree (magnitude);


--
-- Name: ix_reference_standard_certificate_uncertainties_measure_76de; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_measure_76de ON public.reference_standard_certificate_uncertainties USING btree (measurement_type);


--
-- Name: ix_reference_standard_certificate_uncertainties_range_max; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_range_max ON public.reference_standard_certificate_uncertainties USING btree (range_max);


--
-- Name: ix_reference_standard_certificate_uncertainties_range_min; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_range_min ON public.reference_standard_certificate_uncertainties USING btree (range_min);


--
-- Name: ix_reference_standard_certificate_uncertainties_unit; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificate_uncertainties_unit ON public.reference_standard_certificate_uncertainties USING btree (unit);


--
-- Name: ix_reference_standard_certificates_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_approved_by_id ON public.reference_standard_certificates USING btree (approved_by_id);


--
-- Name: ix_reference_standard_certificates_certificate_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_certificate_number ON public.reference_standard_certificates USING btree (certificate_number);


--
-- Name: ix_reference_standard_certificates_controlled_document__82a6; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_controlled_document__82a6 ON public.reference_standard_certificates USING btree (controlled_document_version_id);


--
-- Name: ix_reference_standard_certificates_controlled_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_controlled_document_id ON public.reference_standard_certificates USING btree (controlled_document_id);


--
-- Name: ix_reference_standard_certificates_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_created_by_id ON public.reference_standard_certificates USING btree (created_by_id);


--
-- Name: ix_reference_standard_certificates_expiration_date; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_expiration_date ON public.reference_standard_certificates USING btree (expiration_date);


--
-- Name: ix_reference_standard_certificates_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_id ON public.reference_standard_certificates USING btree (id);


--
-- Name: ix_reference_standard_certificates_is_current; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_is_current ON public.reference_standard_certificates USING btree (is_current);


--
-- Name: ix_reference_standard_certificates_reference_standard_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_reference_standard_id ON public.reference_standard_certificates USING btree (reference_standard_id);


--
-- Name: ix_reference_standard_certificates_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_certificates_status ON public.reference_standard_certificates USING btree (status);


--
-- Name: ix_reference_standard_uncertainties_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_uncertainties_id ON public.reference_standard_uncertainties USING btree (id);


--
-- Name: ix_reference_standard_uncertainties_reference_standard_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standard_uncertainties_reference_standard_id ON public.reference_standard_uncertainties USING btree (reference_standard_id);


--
-- Name: ix_reference_standards_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_id ON public.reference_standards USING btree (id);


--
-- Name: ix_reference_standards_internal_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_internal_code ON public.reference_standards USING btree (internal_code);


--
-- Name: ix_reference_standards_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_magnitude ON public.reference_standards USING btree (magnitude);


--
-- Name: ix_reference_standards_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_name ON public.reference_standards USING btree (name);


--
-- Name: ix_reference_standards_next_calibration_on; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_next_calibration_on ON public.reference_standards USING btree (next_calibration_on);


--
-- Name: ix_reference_standards_owner_company; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_owner_company ON public.reference_standards USING btree (owner_company);


--
-- Name: ix_reference_standards_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_reference_standards_status ON public.reference_standards USING btree (status);


--
-- Name: ix_roles_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_roles_id ON public.roles USING btree (id);


--
-- Name: ix_roles_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_roles_name ON public.roles USING btree (name);


--
-- Name: ix_service_order_items_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_order_items_id ON public.service_order_items USING btree (id);


--
-- Name: ix_service_order_items_service_order_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_order_items_service_order_id ON public.service_order_items USING btree (service_order_id);


--
-- Name: ix_service_orders_advisor_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_advisor_id ON public.service_orders USING btree (advisor_id);


--
-- Name: ix_service_orders_client_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_client_id ON public.service_orders USING btree (client_id);


--
-- Name: ix_service_orders_folio; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_service_orders_folio ON public.service_orders USING btree (folio);


--
-- Name: ix_service_orders_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_id ON public.service_orders USING btree (id);


--
-- Name: ix_service_orders_quotation_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_quotation_id ON public.service_orders USING btree (quotation_id);


--
-- Name: ix_service_orders_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_status ON public.service_orders USING btree (status);


--
-- Name: ix_service_orders_technician_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_service_orders_technician_id ON public.service_orders USING btree (technician_id);


--
-- Name: ix_service_orders_work_order_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_service_orders_work_order_number ON public.service_orders USING btree (work_order_number);


--
-- Name: ix_technical_profile_allowed_patterns_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_id ON public.technical_profile_allowed_patterns USING btree (id);


--
-- Name: ix_technical_profile_allowed_patterns_pattern_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_pattern_code ON public.technical_profile_allowed_patterns USING btree (pattern_code);


--
-- Name: ix_technical_profile_allowed_patterns_pattern_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_pattern_id ON public.technical_profile_allowed_patterns USING btree (pattern_id);


--
-- Name: ix_technical_profile_allowed_patterns_technical_profile_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profile_allowed_patterns_technical_profile_id ON public.technical_profile_allowed_patterns USING btree (technical_profile_id);


--
-- Name: ix_technical_profiles_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_approved_by_id ON public.technical_profiles USING btree (approved_by_id);


--
-- Name: ix_technical_profiles_calibration_scope; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_calibration_scope ON public.technical_profiles USING btree (calibration_scope);


--
-- Name: ix_technical_profiles_certificate_template_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_certificate_template_document_id ON public.technical_profiles USING btree (certificate_template_document_id);


--
-- Name: ix_technical_profiles_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_technical_profiles_code ON public.technical_profiles USING btree (code);


--
-- Name: ix_technical_profiles_created_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_created_by_id ON public.technical_profiles USING btree (created_by_id);


--
-- Name: ix_technical_profiles_equipment_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_equipment_type ON public.technical_profiles USING btree (equipment_type);


--
-- Name: ix_technical_profiles_field_sheet_template_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_field_sheet_template_document_id ON public.technical_profiles USING btree (field_sheet_template_document_id);


--
-- Name: ix_technical_profiles_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_id ON public.technical_profiles USING btree (id);


--
-- Name: ix_technical_profiles_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_magnitude ON public.technical_profiles USING btree (magnitude);


--
-- Name: ix_technical_profiles_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_name ON public.technical_profiles USING btree (name);


--
-- Name: ix_technical_profiles_procedure_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_procedure_document_id ON public.technical_profiles USING btree (procedure_document_id);


--
-- Name: ix_technical_profiles_procedure_interpretation_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_procedure_interpretation_id ON public.technical_profiles USING btree (procedure_interpretation_id);


--
-- Name: ix_technical_profiles_service_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_service_type ON public.technical_profiles USING btree (service_type);


--
-- Name: ix_technical_profiles_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_status ON public.technical_profiles USING btree (status);


--
-- Name: ix_technical_profiles_uncertainty_source_document_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_technical_profiles_uncertainty_source_document_id ON public.technical_profiles USING btree (uncertainty_source_document_id);


--
-- Name: ix_uncertainty_calculations_field_sheet_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_field_sheet_id ON public.uncertainty_calculations USING btree (field_sheet_id);


--
-- Name: ix_uncertainty_calculations_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_status ON public.uncertainty_calculations USING btree (status);


--
-- Name: ix_uncertainty_calculations_uncertainty_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_uncertainty_model_id ON public.uncertainty_calculations USING btree (uncertainty_model_id);


--
-- Name: ix_uncertainty_calculations_uncertainty_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_calculations_uncertainty_model_version_id ON public.uncertainty_calculations USING btree (uncertainty_model_version_id);


--
-- Name: ix_uncertainty_components_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_key ON public.uncertainty_components USING btree (key);


--
-- Name: ix_uncertainty_components_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_model_id ON public.uncertainty_components USING btree (model_id);


--
-- Name: ix_uncertainty_components_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_model_version_id ON public.uncertainty_components USING btree (model_version_id);


--
-- Name: ix_uncertainty_components_source_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_components_source_type ON public.uncertainty_components USING btree (source_type);


--
-- Name: ix_uncertainty_formulas_is_active_formula; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_is_active_formula ON public.uncertainty_formulas USING btree (is_active_formula);


--
-- Name: ix_uncertainty_formulas_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_key ON public.uncertainty_formulas USING btree (key);


--
-- Name: ix_uncertainty_formulas_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_model_id ON public.uncertainty_formulas USING btree (model_id);


--
-- Name: ix_uncertainty_formulas_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_model_version_id ON public.uncertainty_formulas USING btree (model_version_id);


--
-- Name: ix_uncertainty_formulas_result_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_formulas_result_key ON public.uncertainty_formulas USING btree (result_key);


--
-- Name: ix_uncertainty_model_exceptions_alternate_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_alternate_model_id ON public.uncertainty_model_exceptions USING btree (alternate_model_id);


--
-- Name: ix_uncertainty_model_exceptions_alternate_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_alternate_model_version_id ON public.uncertainty_model_exceptions USING btree (alternate_model_version_id);


--
-- Name: ix_uncertainty_model_exceptions_base_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_base_model_id ON public.uncertainty_model_exceptions USING btree (base_model_id);


--
-- Name: ix_uncertainty_model_exceptions_base_model_version_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_base_model_version_id ON public.uncertainty_model_exceptions USING btree (base_model_version_id);


--
-- Name: ix_uncertainty_model_exceptions_equipment_model; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_equipment_model ON public.uncertainty_model_exceptions USING btree (equipment_model);


--
-- Name: ix_uncertainty_model_exceptions_equipment_type; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_equipment_type ON public.uncertainty_model_exceptions USING btree (equipment_type);


--
-- Name: ix_uncertainty_model_exceptions_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_magnitude ON public.uncertainty_model_exceptions USING btree (magnitude);


--
-- Name: ix_uncertainty_model_exceptions_procedure_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_procedure_id ON public.uncertainty_model_exceptions USING btree (procedure_id);


--
-- Name: ix_uncertainty_model_exceptions_profile_key; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_profile_key ON public.uncertainty_model_exceptions USING btree (profile_key);


--
-- Name: ix_uncertainty_model_exceptions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_exceptions_status ON public.uncertainty_model_exceptions USING btree (status);


--
-- Name: ix_uncertainty_model_versions_approved_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_approved_by_id ON public.uncertainty_model_versions USING btree (approved_by_id);


--
-- Name: ix_uncertainty_model_versions_model_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_model_id ON public.uncertainty_model_versions USING btree (model_id);


--
-- Name: ix_uncertainty_model_versions_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_status ON public.uncertainty_model_versions USING btree (status);


--
-- Name: ix_uncertainty_model_versions_submitted_by_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_submitted_by_id ON public.uncertainty_model_versions USING btree (submitted_by_id);


--
-- Name: ix_uncertainty_model_versions_version_number; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_model_versions_version_number ON public.uncertainty_model_versions USING btree (version_number);


--
-- Name: ix_uncertainty_models_code; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_code ON public.uncertainty_models USING btree (code);


--
-- Name: ix_uncertainty_models_equipment_family; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_equipment_family ON public.uncertainty_models USING btree (equipment_family);


--
-- Name: ix_uncertainty_models_magnitude; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_magnitude ON public.uncertainty_models USING btree (magnitude);


--
-- Name: ix_uncertainty_models_name; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_name ON public.uncertainty_models USING btree (name);


--
-- Name: ix_uncertainty_models_status; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_status ON public.uncertainty_models USING btree (status);


--
-- Name: ix_uncertainty_models_version; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_uncertainty_models_version ON public.uncertainty_models USING btree (version);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: uq_calibration_procedures_code_version_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_calibration_procedures_code_version_active ON public.calibration_procedures USING btree (code, version) WHERE (is_active = true);


--
-- Name: uq_catalog_items_internal_key_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_catalog_items_internal_key_active ON public.catalog_items USING btree (internal_key) WHERE ((is_active = true) AND (internal_key IS NOT NULL));


--
-- Name: uq_certificates_active_field_sheet; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_certificates_active_field_sheet ON public.certificates USING btree (field_sheet_id) WHERE (is_active IS TRUE);


--
-- Name: uq_controlled_document_one_active_version; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_controlled_document_one_active_version ON public.controlled_document_versions USING btree (document_id) WHERE ((status)::text = 'active'::text);


--
-- Name: uq_field_sheets_active_equipment; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_field_sheets_active_equipment ON public.field_sheets USING btree (equipment_id) WHERE (is_active IS TRUE);


--
-- Name: uq_reference_standard_current_certificate; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_reference_standard_current_certificate ON public.reference_standard_certificates USING btree (reference_standard_id) WHERE (is_current = true);


--
-- Name: uq_reference_standards_internal_code_active; Type: INDEX; Schema: public; Owner: saulcortes
--

CREATE UNIQUE INDEX uq_reference_standards_internal_code_active ON public.reference_standards USING btree (internal_code) WHERE (is_active = true);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: certificates certificates_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: certificates certificates_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: certificates certificates_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: client_contacts client_contacts_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.client_contacts
    ADD CONSTRAINT client_contacts_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: controlled_document_versions controlled_document_versions_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: controlled_document_versions controlled_document_versions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.controlled_documents(id);


--
-- Name: controlled_document_versions controlled_document_versions_reviewed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_reviewed_by_id_fkey FOREIGN KEY (reviewed_by_id) REFERENCES public.users(id);


--
-- Name: controlled_document_versions controlled_document_versions_uploaded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_document_versions
    ADD CONSTRAINT controlled_document_versions_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id);


--
-- Name: controlled_documents controlled_documents_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.controlled_documents
    ADD CONSTRAINT controlled_documents_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: credit_notes credit_notes_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes
    ADD CONSTRAINT credit_notes_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: credit_notes credit_notes_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.credit_notes
    ADD CONSTRAINT credit_notes_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: document_interpretations document_interpretations_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: document_interpretations document_interpretations_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: document_interpretations document_interpretations_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.controlled_documents(id);


--
-- Name: document_interpretations document_interpretations_document_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.document_interpretations
    ADD CONSTRAINT document_interpretations_document_version_id_fkey FOREIGN KEY (document_version_id) REFERENCES public.controlled_document_versions(id);


--
-- Name: equipment equipment_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: equipment equipment_service_order_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_service_order_item_id_fkey FOREIGN KEY (service_order_item_id) REFERENCES public.service_order_items(id);


--
-- Name: field_sheet_reference_standards field_sheet_reference_standards_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT field_sheet_reference_standards_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: field_sheet_reference_standards field_sheet_reference_standards_reference_standard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT field_sheet_reference_standards_reference_standard_id_fkey FOREIGN KEY (reference_standard_id) REFERENCES public.reference_standards(id);


--
-- Name: field_sheet_results field_sheet_results_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_results
    ADD CONSTRAINT field_sheet_results_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: field_sheets field_sheets_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT field_sheets_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: calibration_procedures fk_calibration_procedures_uncertainty_model_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures
    ADD CONSTRAINT fk_calibration_procedures_uncertainty_model_id FOREIGN KEY (uncertainty_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: calibration_procedures fk_calibration_procedures_uncertainty_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.calibration_procedures
    ADD CONSTRAINT fk_calibration_procedures_uncertainty_model_version_id FOREIGN KEY (uncertainty_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: certificates fk_certificates_authenticated_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_authenticated_by_id_users FOREIGN KEY (authenticated_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_capture_started_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_capture_started_by_id FOREIGN KEY (capture_started_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_final_pdf_uploaded_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_final_pdf_uploaded_by_id FOREIGN KEY (final_pdf_uploaded_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_quality_reviewed_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_quality_reviewed_by_id FOREIGN KEY (quality_reviewed_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_released_to_client_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_released_to_client_by_id FOREIGN KEY (released_to_client_by_id) REFERENCES public.users(id);


--
-- Name: certificates fk_certificates_sent_to_quality_by_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT fk_certificates_sent_to_quality_by_id FOREIGN KEY (sent_to_quality_by_id) REFERENCES public.users(id);


--
-- Name: field_sheet_reference_standards fk_field_sheet_reference_standards_certificate_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT fk_field_sheet_reference_standards_certificate_id FOREIGN KEY (reference_standard_certificate_id) REFERENCES public.reference_standard_certificates(id);


--
-- Name: field_sheet_reference_standards fk_field_sheet_reference_standards_uncertainty_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheet_reference_standards
    ADD CONSTRAINT fk_field_sheet_reference_standards_uncertainty_id FOREIGN KEY (selected_uncertainty_id) REFERENCES public.reference_standard_certificate_uncertainties(id);


--
-- Name: field_sheets fk_field_sheets_calibration_procedure_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT fk_field_sheets_calibration_procedure_id FOREIGN KEY (calibration_procedure_id) REFERENCES public.calibration_procedures(id);


--
-- Name: field_sheets fk_field_sheets_returned_to_technician_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.field_sheets
    ADD CONSTRAINT fk_field_sheets_returned_to_technician_by_id_users FOREIGN KEY (returned_to_technician_by_id) REFERENCES public.users(id);


--
-- Name: quotation_items fk_quotation_items_catalog_item_id_catalog_items; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT fk_quotation_items_catalog_item_id_catalog_items FOREIGN KEY (catalog_item_id) REFERENCES public.catalog_items(id);


--
-- Name: service_orders fk_service_orders_advisor_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT fk_service_orders_advisor_id_users FOREIGN KEY (advisor_id) REFERENCES public.users(id);


--
-- Name: service_orders fk_service_orders_technician_id_users; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT fk_service_orders_technician_id_users FOREIGN KEY (technician_id) REFERENCES public.users(id);


--
-- Name: uncertainty_calculations fk_uncertainty_calculations_uncertainty_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT fk_uncertainty_calculations_uncertainty_model_version_id FOREIGN KEY (uncertainty_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_components fk_uncertainty_components_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components
    ADD CONSTRAINT fk_uncertainty_components_model_version_id FOREIGN KEY (model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_formulas fk_uncertainty_formulas_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas
    ADD CONSTRAINT fk_uncertainty_formulas_model_version_id FOREIGN KEY (model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_model_exceptions fk_uncertainty_model_exceptions_alternate_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT fk_uncertainty_model_exceptions_alternate_model_version_id FOREIGN KEY (alternate_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: uncertainty_model_exceptions fk_uncertainty_model_exceptions_base_model_version_id; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT fk_uncertainty_model_exceptions_base_model_version_id FOREIGN KEY (base_model_version_id) REFERENCES public.uncertainty_model_versions(id);


--
-- Name: invoice_items invoice_items_certificate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_certificate_id_fkey FOREIGN KEY (certificate_id) REFERENCES public.certificates(id);


--
-- Name: invoice_items invoice_items_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: invoice_items invoice_items_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: invoice_items invoice_items_quotation_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_quotation_item_id_fkey FOREIGN KEY (quotation_item_id) REFERENCES public.quotation_items(id);


--
-- Name: invoice_payments invoice_payments_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments
    ADD CONSTRAINT invoice_payments_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: invoice_payments invoice_payments_registered_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoice_payments
    ADD CONSTRAINT invoice_payments_registered_by_id_fkey FOREIGN KEY (registered_by_id) REFERENCES public.users(id);


--
-- Name: invoices invoices_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: invoices invoices_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: invoices invoices_fiscal_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_fiscal_client_id_fkey FOREIGN KEY (fiscal_client_id) REFERENCES public.clients(id);


--
-- Name: invoices invoices_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id);


--
-- Name: invoices invoices_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: invoices invoices_updated_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_updated_by_id_fkey FOREIGN KEY (updated_by_id) REFERENCES public.users(id);


--
-- Name: quotation_items quotation_items_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id);


--
-- Name: quotations quotations_advisor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_advisor_id_fkey FOREIGN KEY (advisor_id) REFERENCES public.users(id);


--
-- Name: quotations quotations_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: reference_standard_certificates reference_standard_certificat_controlled_document_version__fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificat_controlled_document_version__fkey FOREIGN KEY (controlled_document_version_id) REFERENCES public.controlled_document_versions(id);


--
-- Name: reference_standard_certificate_uncertainties reference_standard_certificate_uncertaintie_certificate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificate_uncertainties
    ADD CONSTRAINT reference_standard_certificate_uncertaintie_certificate_id_fkey FOREIGN KEY (certificate_id) REFERENCES public.reference_standard_certificates(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_controlled_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_controlled_document_id_fkey FOREIGN KEY (controlled_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: reference_standard_certificates reference_standard_certificates_reference_standard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_certificates
    ADD CONSTRAINT reference_standard_certificates_reference_standard_id_fkey FOREIGN KEY (reference_standard_id) REFERENCES public.reference_standards(id);


--
-- Name: reference_standard_uncertainties reference_standard_uncertainties_reference_standard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.reference_standard_uncertainties
    ADD CONSTRAINT reference_standard_uncertainties_reference_standard_id_fkey FOREIGN KEY (reference_standard_id) REFERENCES public.reference_standards(id);


--
-- Name: service_order_items service_order_items_quotation_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items
    ADD CONSTRAINT service_order_items_quotation_item_id_fkey FOREIGN KEY (quotation_item_id) REFERENCES public.quotation_items(id);


--
-- Name: service_order_items service_order_items_service_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_order_items
    ADD CONSTRAINT service_order_items_service_order_id_fkey FOREIGN KEY (service_order_id) REFERENCES public.service_orders(id);


--
-- Name: service_orders service_orders_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT service_orders_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: service_orders service_orders_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.service_orders
    ADD CONSTRAINT service_orders_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id);


--
-- Name: technical_profile_allowed_patterns technical_profile_allowed_patterns_pattern_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns
    ADD CONSTRAINT technical_profile_allowed_patterns_pattern_id_fkey FOREIGN KEY (pattern_id) REFERENCES public.reference_standards(id);


--
-- Name: technical_profile_allowed_patterns technical_profile_allowed_patterns_technical_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profile_allowed_patterns
    ADD CONSTRAINT technical_profile_allowed_patterns_technical_profile_id_fkey FOREIGN KEY (technical_profile_id) REFERENCES public.technical_profiles(id);


--
-- Name: technical_profiles technical_profiles_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: technical_profiles technical_profiles_certificate_template_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_certificate_template_document_id_fkey FOREIGN KEY (certificate_template_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: technical_profiles technical_profiles_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: technical_profiles technical_profiles_field_sheet_template_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_field_sheet_template_document_id_fkey FOREIGN KEY (field_sheet_template_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: technical_profiles technical_profiles_procedure_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_procedure_document_id_fkey FOREIGN KEY (procedure_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: technical_profiles technical_profiles_procedure_interpretation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_procedure_interpretation_id_fkey FOREIGN KEY (procedure_interpretation_id) REFERENCES public.document_interpretations(id);


--
-- Name: technical_profiles technical_profiles_uncertainty_source_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.technical_profiles
    ADD CONSTRAINT technical_profiles_uncertainty_source_document_id_fkey FOREIGN KEY (uncertainty_source_document_id) REFERENCES public.controlled_documents(id);


--
-- Name: uncertainty_calculations uncertainty_calculations_field_sheet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT uncertainty_calculations_field_sheet_id_fkey FOREIGN KEY (field_sheet_id) REFERENCES public.field_sheets(id);


--
-- Name: uncertainty_calculations uncertainty_calculations_uncertainty_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_calculations
    ADD CONSTRAINT uncertainty_calculations_uncertainty_model_id_fkey FOREIGN KEY (uncertainty_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_components uncertainty_components_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_components
    ADD CONSTRAINT uncertainty_components_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_formulas uncertainty_formulas_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_formulas
    ADD CONSTRAINT uncertainty_formulas_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_alternate_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_alternate_model_id_fkey FOREIGN KEY (alternate_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_authorized_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_authorized_by_id_fkey FOREIGN KEY (authorized_by_id) REFERENCES public.users(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_base_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_base_model_id_fkey FOREIGN KEY (base_model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_exceptions uncertainty_model_exceptions_procedure_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_exceptions
    ADD CONSTRAINT uncertainty_model_exceptions_procedure_id_fkey FOREIGN KEY (procedure_id) REFERENCES public.calibration_procedures(id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.users(id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.uncertainty_models(id);


--
-- Name: uncertainty_model_versions uncertainty_model_versions_submitted_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.uncertainty_model_versions
    ADD CONSTRAINT uncertainty_model_versions_submitted_by_id_fkey FOREIGN KEY (submitted_by_id) REFERENCES public.users(id);


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: saulcortes
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: saulcortes
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict BcXx1Bw0pwFXmQVCGOl0FY7ehozlYIckdap1r6ym5LwYYsxd0xlwmoDo7Usr5DY

