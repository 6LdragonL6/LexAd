"""add_brands_and_material_brand_id

Revision ID: 294f05fbf95c
Revises: a4b7d1c6e825
Create Date: 2026-07-11 20:33:11.890439
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '294f05fbf95c'
down_revision: Union[str, None] = 'a4b7d1c6e825'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'brands',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('industry', sa.String(50), nullable=False, server_default=''),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.Enum('active', 'archived', name='brandstatus'), nullable=False, server_default='active'),
        sa.Column('created_by_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
    )
    op.create_index(op.f('ix_brands_name'), 'brands', ['name'], unique=True)
    op.create_index(op.f('ix_brands_status'), 'brands', ['status'])

    with op.batch_alter_table('materials') as batch_op:
        batch_op.add_column(sa.Column('brand_id', sa.String(36), nullable=True))
        batch_op.create_index(op.f('ix_materials_brand_id'), ['brand_id'])
        batch_op.create_foreign_key('fk_materials_brand_id', 'brands', ['brand_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('materials') as batch_op:
        batch_op.drop_constraint('fk_materials_brand_id', type_='foreignkey')
        batch_op.drop_index(op.f('ix_materials_brand_id'))
        batch_op.drop_column('brand_id')

    op.drop_table('brands')
    # PostgreSQL: drop the enum type so re-upgrade does not fail
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS brandstatus')
