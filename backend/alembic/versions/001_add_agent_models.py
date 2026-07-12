"""Add Band of Agents database models

Revision ID: 001_add_agent_models
Revises: 
Create Date: 2024-06-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_agent_models'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (once each)
    op.execute("""
        CREATE TYPE escalationlevel AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    """)
    op.execute("""
        CREATE TYPE agenttype AS ENUM ('CLINICAL_REVIEW', 'COMPLIANCE_PRIVACY', 'MEDICAL_HISTORY', 
                                       'TREATMENT_RECOMMENDATION', 'INSURANCE_VERIFICATION', 
                                       'TRIAGE_ESCALATION', 'FOLLOWUP_COORDINATION')
    """)
    op.execute("""
        CREATE TYPE agenteventtype AS ENUM ('AGENT_STARTED', 'AGENT_PROCESSING', 'AGENT_COMPLETED', 
                                            'AGENT_FAILED', 'AGENT_WAITING', 'RECOMMENDATION_GENERATED', 
                                            'CONSENSUS_REACHED', 'ESCALATION_TRIGGERED')
    """)
    
    # Create agent_processing_reports table
    op.create_table(
        'agent_processing_reports',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('consultation_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_duration_seconds', sa.Float(), nullable=True),
        sa.Column('agents_executed', postgresql.JSON(), server_default='[]', nullable=False),
        sa.Column('agents_failed', postgresql.JSON(), server_default='[]', nullable=False),
        sa.Column('agents_skipped', postgresql.JSON(), server_default='[]', nullable=False),
        sa.Column('consensus_score', sa.Float(), nullable=False),
        sa.Column('overall_risk_score', sa.Float(), nullable=False),
        sa.Column('escalation_triggered', sa.Boolean(), nullable=False),
        sa.Column('escalation_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='escalationlevel'), nullable=True),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('master_recommendations', postgresql.JSON(), nullable=True),
        sa.Column('critical_alerts', postgresql.JSON(), nullable=True),
        sa.Column('compliance_flags', postgresql.JSON(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['consultation_id'], ['consultations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('consultation_id')
    )
    op.create_index(
        'ix_agent_processing_reports_consultation_id',
        'agent_processing_reports',
        ['consultation_id'],
        unique=True
    )
    
    # Create agent_events table
    op.create_table(
        'agent_events',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('processing_report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('agent_type', sa.Enum('CLINICAL_REVIEW', 'COMPLIANCE_PRIVACY', 'MEDICAL_HISTORY', 'TREATMENT_RECOMMENDATION', 'INSURANCE_VERIFICATION', 'TRIAGE_ESCALATION', 'FOLLOWUP_COORDINATION', name='agenttype'), nullable=False),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('event_type', sa.Enum('AGENT_STARTED', 'AGENT_PROCESSING', 'AGENT_COMPLETED', 'AGENT_FAILED', 'AGENT_WAITING', 'RECOMMENDATION_GENERATED', 'CONSENSUS_REACHED', 'ESCALATION_TRIGGERED', name='agenteventtype'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('input_context', postgresql.JSON(), nullable=True),
        sa.Column('agent_output', postgresql.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('waited_for_agents', postgresql.JSON(), server_default='[]', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['processing_report_id'], ['agent_processing_reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_agent_events_processing_report_id',
        'agent_events',
        ['processing_report_id']
    )
    op.create_index(
        'ix_agent_events_agent_type',
        'agent_events',
        ['agent_type']
    )
    op.create_index(
        'ix_agent_events_agent_id',
        'agent_events',
        ['agent_id']
    )
    op.create_index(
        'ix_agent_events_timestamp',
        'agent_events',
        ['timestamp']
    )
    
    # Create agent_recommendations table
    op.create_table(
        'agent_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('processing_report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('agent_event_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('source_agent', sa.Enum('CLINICAL_REVIEW', 'COMPLIANCE_PRIVACY', 'MEDICAL_HISTORY', 'TREATMENT_RECOMMENDATION', 'INSURANCE_VERIFICATION', 'TRIAGE_ESCALATION', 'FOLLOWUP_COORDINATION', name='agenttype'), nullable=False),
        sa.Column('source_agent_id', sa.String(length=100), nullable=False),
        sa.Column('recommendation_type', sa.String(length=100), nullable=False),
        sa.Column('recommendation_text', sa.Text(), nullable=False),
        sa.Column('recommendation_data', postgresql.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False),
        sa.Column('supporting_evidence', postgresql.JSON(), server_default='[]', nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('overridden', sa.Boolean(), nullable=False),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('overridden_by_agent', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_event_id'], ['agent_events.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['processing_report_id'], ['agent_processing_reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_agent_recommendations_processing_report_id',
        'agent_recommendations',
        ['processing_report_id']
    )
    op.create_index(
        'ix_agent_recommendations_source_agent',
        'agent_recommendations',
        ['source_agent']
    )
    
    # Create escalation_events table
    op.create_table(
        'escalation_events',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('processing_report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('escalation_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='escalationlevel'), nullable=False),
        sa.Column('escalation_reason', sa.String(length=255), nullable=False),
        sa.Column('escalation_type', sa.String(length=100), nullable=False),
        sa.Column('triggered_by_agent', sa.Enum('CLINICAL_REVIEW', 'COMPLIANCE_PRIVACY', 'MEDICAL_HISTORY', 'TREATMENT_RECOMMENDATION', 'INSURANCE_VERIFICATION', 'TRIAGE_ESCALATION', 'FOLLOWUP_COORDINATION', name='agenttype'), nullable=False),
        sa.Column('triggered_by_agent_id', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('required_action', sa.Text(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=False),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['processing_report_id'], ['agent_processing_reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_escalation_events_processing_report_id',
        'escalation_events',
        ['processing_report_id']
    )
    op.create_index(
        'ix_escalation_events_escalation_level',
        'escalation_events',
        ['escalation_level']
    )
    
    # Create agent_consensus table
    op.create_table(
        'agent_consensus',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column('processing_report_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('total_agents_executed', sa.Integer(), nullable=False),
        sa.Column('total_agents_agreed', sa.Integer(), nullable=False),
        sa.Column('consensus_percentage', sa.Float(), nullable=False),
        sa.Column('primary_diagnosis', sa.String(length=500), nullable=True),
        sa.Column('diagnosis_confidence', sa.Float(), nullable=True),
        sa.Column('primary_treatment_plan', sa.Text(), nullable=True),
        sa.Column('treatment_confidence', sa.Float(), nullable=True),
        sa.Column('risk_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='escalationlevel'), nullable=False),
        sa.Column('risk_factors', postgresql.JSON(), server_default='[]', nullable=True),
        sa.Column('agent_agreements', postgresql.JSON(), nullable=True),
        sa.Column('conflicting_recommendations', postgresql.JSON(), server_default='[]', nullable=True),
        sa.Column('final_recommendations', postgresql.JSON(), server_default='[]', nullable=True),
        sa.Column('follow_up_date', sa.DateTime(), nullable=True),
        sa.Column('requires_doctor_review', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['processing_report_id'], ['agent_processing_reports.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('processing_report_id')
    )
    op.create_index(
        'ix_agent_consensus_processing_report_id',
        'agent_consensus',
        ['processing_report_id'],
        unique=True
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_agent_consensus_processing_report_id', table_name='agent_consensus')
    op.drop_table('agent_consensus')
    
    op.drop_index('ix_escalation_events_escalation_level', table_name='escalation_events')
    op.drop_index('ix_escalation_events_processing_report_id', table_name='escalation_events')
    op.drop_table('escalation_events')
    
    op.drop_index('ix_agent_recommendations_source_agent', table_name='agent_recommendations')
    op.drop_index('ix_agent_recommendations_processing_report_id', table_name='agent_recommendations')
    op.drop_table('agent_recommendations')
    
    op.drop_index('ix_agent_events_timestamp', table_name='agent_events')
    op.drop_index('ix_agent_events_agent_id', table_name='agent_events')
    op.drop_index('ix_agent_events_agent_type', table_name='agent_events')
    op.drop_index('ix_agent_events_processing_report_id', table_name='agent_events')
    op.drop_table('agent_events')
    
    op.drop_index('ix_agent_processing_reports_consultation_id', table_name='agent_processing_reports')
    op.drop_table('agent_processing_reports')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS agenteventtype")
    op.execute("DROP TYPE IF EXISTS agenttype")
    op.execute("DROP TYPE IF EXISTS escalationlevel")