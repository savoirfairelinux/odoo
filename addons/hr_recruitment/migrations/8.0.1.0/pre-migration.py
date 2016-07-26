# -*- coding: utf-8 -*-
# © 2016 Savoir-faire Linux <https://www.savoirfairelinux.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


column_drops = [
    ('hr_applicant', 'date'),
    ('hr_recruitment_stage', 'state'),
]

column_renames = {
    'hr_applicant': [
        ('response', 'response_id'),
    ]
}


@openupgrade.migrate()
def migrate(cr, version):
    if not version:
        return

    openupgrade.drop_columns(cr, column_drops)
    openupgrade.rename_columns(cr, column_renames)

    # Update priorities
    prioty_updates = [
        ('z5', '5'),
        ('z4', '4'),
        ('z3', '3'),
        ('z2', '2'),
        ('z1', '1'),
    ]

    for priorities in prioty_updates:
        cr.execute(
            "UPDATE hr_applicant SET priority = %s "
            "WHERE priority = %s", priorities
        )

    prioty_updates = [
        ('0', 'z5'),
        ('1', 'z4'),
        ('2', 'z3'),
        ('3', 'z2'),
        ('4', 'z1'),
    ]

    for priorities in prioty_updates:
        cr.execute(
            "UPDATE hr_applicant SET priority = %s "
            "WHERE priority = %s", priorities
        )

    cr.execute(
        "ALTER TABLE hr_job "
        "DROP CONSTRAINT IF EXISTS hr_job_survey_id_fkey")

    cr.execute(
        "ALTER TABLE hr_applicant "
        "DROP CONSTRAINT IF EXISTS hr_applicant_response_id_fkey")

    cr.execute(
        "UPDATE hr_applicant SET response_id = NULL WHERE response_id = 0")

    # Fix reference to categ_meet_interview
    cr.execute(
        "UPDATE ir_model_data SET model = 'calendar.event.type' "
        "WHERE module = 'hr_recruitment' AND name = 'categ_meet_interview'")
