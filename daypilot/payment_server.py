"""Payment handoff extension. No payment execution, PIN collection or bank verification."""
import re, time, secrets
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from contextlib import closing
from daypilot.server import mcp, safe
from daypilot.db import connect


def _db():
    c = connect()
    c.execute('CREATE TABLE IF NOT EXISTS payment_drafts (id TEXT PRIMARY KEY, name TEXT, vpa TEXT, amount TEXT, demo INTEGER, created REAL, status TEXT)')
    return c


@mcp.tool()
@safe
def prepare_payment(recipient: str, upi_id: str, amount: str, demo: bool = True) -> dict:
    """Prepare a payment review only. Never pays. Demo mode cannot produce a live link."""
    recipient = recipient.strip()
    upi_id = upi_id.strip()
    if not recipient or len(recipient)>80 or any(ord(x)<32 for x in recipient):
        raise ValueError('Enter a recipient name of 1 to 80 characters.')
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}@[A-Za-z0-9.-]{2,50}', upi_id):
        raise ValueError('Enter a UPI ID in name@provider format. This checks format only.')
    if not re.fullmatch(r'[0-9]{1,5}(?:\.[0-9]{1,2})?', amount.strip()):
        raise ValueError('Enter an amount in rupees with up to two decimal places.')
    value = Decimal(amount.strip())
    if not Decimal('0.01') <= value <= Decimal('10000'):
        raise ValueError('Prototype amount must be between 0.01 and 10,000 rupees.')
    amount = f'{value:.2f}'
    pid = secrets.token_urlsafe(18)
    with closing(_db()) as c, c:
        c.execute('DELETE FROM payment_drafts WHERE status=? AND created<?', ('draft', time.time()-600))
        c.execute('INSERT INTO payment_drafts VALUES (?,?,?,?,?,?,?)',(pid,recipient,upi_id,amount,int(demo),time.time(),'draft'))
    spoken = f'{"Demo only. " if demo else ""}Payment request: {amount} rupees to {recipient}. UPI ID: {" ".join(upi_id.replace("@", "@"))}. Recipient is not verified. Review the details. No money has moved. Confirm payment to prepare the handoff, or cancel payment.'
    return {'ok':True,'payment_id':pid,'spoken_summary':spoken,'recipient':recipient,'upi_id':upi_id,'amount':amount,'demo':demo}


@mcp.tool()
@safe
def confirm_payment_handoff(payment_id: str) -> dict:
    """Confirm the reviewed request, not the payment. Return a link only for non-demo drafts."""
    with closing(_db()) as c, c:
        c.execute('BEGIN IMMEDIATE')
        r=c.execute('SELECT * FROM payment_drafts WHERE id=?',(payment_id,)).fetchone()
        if not r or r['status']!='draft' or time.time()-r['created']>600:
            raise ValueError('Payment draft is missing, expired, or already handled. Prepare a new one.')
        c.execute('UPDATE payment_drafts SET status=? WHERE id=?',('handoff_prepared',payment_id))
        demo=bool(r['demo'])
        link=None if demo else 'upi://pay?'+urlencode({'pa':r['vpa'],'pn':r['name'],'am':r['amount'],'cu':'INR'})
    return {'ok':True,'demo':demo,'link':link,'spoken_summary': 'Demo confirmed. No payment app will open and no money has moved.' if demo else 'Handoff prepared. No money has moved. Open your UPI app using the link, verify the actual recipient and amount there, then authorize only if correct. DayPilot cannot verify payment status.'}


@mcp.tool()
@safe
def cancel_payment(payment_id: str) -> dict:
    """Cancel an unconfirmed payment draft. Cannot reverse an external transaction."""
    with closing(_db()) as c, c:
        cur=c.execute('DELETE FROM payment_drafts WHERE id=? AND status=?',(payment_id,'draft'))
        if cur.rowcount!=1: raise ValueError('No pending payment draft to cancel.')
    return {'ok':True,'spoken_summary':'Payment draft cancelled. No money has moved.'}


if __name__=='__main__':
    mcp.run()
