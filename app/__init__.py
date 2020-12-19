import os, sys, configparser, warnings
from flask import (Flask, redirect, render_template, request, session, url_for)
from app import consent, alert, experiment, complete, error
from .io import write_metadata
from .utils import gen_code
__version__ = '1.0'

## Define root directory.
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

## Load and parse configuration file.
cfg = configparser.ConfigParser()
cfg.read(os.path.join(ROOT_DIR, 'app.ini'))

## Ensure output directories exist.
data_dir = os.path.join(ROOT_DIR, cfg['IO']['DATA'])
if not os.path.isdir(data_dir): os.makedirs(data_dir)
meta_dir = os.path.join(ROOT_DIR, cfg['IO']['METADATA'])
if not os.path.isdir(meta_dir): os.makedirs(meta_dir)
reject_dir = os.path.join(ROOT_DIR, cfg['IO']['REJECT'])
if not os.path.isdir(reject_dir): os.makedirs(reject_dir)

## Check Flask mode; if debug mode, clear session variable.
debug = cfg['FLASK'].getboolean('DEBUG')
if debug:
    warnings.warn("WARNING: Flask currently in debug mode. This should be changed prior to production.")

## Check Flask password.
secret_key = cfg['FLASK']['SECRET_KEY']
if secret_key == "PLEASE_CHANGE_THIS":
    warnings.warn("WARNING: Flask password is currently default. This should be changed prior to production.")

## Initialize Flask application.
app = Flask(__name__)
app.secret_key = secret_key

## Apply blueprints to the application.
app.register_blueprint(consent.bp)
app.register_blueprint(alert.bp)
app.register_blueprint(experiment.bp)
app.register_blueprint(complete.bp)
app.register_blueprint(error.bp)

## Define root node.
@app.route('/')
def index():

    ## Debug mode: clear session.
    if debug:
        session.clear()

    ## Store directories in session object.
    session['data'] = data_dir
    session['metadata'] = meta_dir
    session['reject'] = reject_dir

    ## Record incoming metadata.
    info = dict(
        workerId     = request.args.get('workerId'),        # MTurk metadata
        assignmentId = request.args.get('assignmentId'),    # MTurk metadata
        hitId        = request.args.get('hitId'),           # MTurk metadata
        subId        = gen_code(24),                        # NivTurk metadata
        a            = request.args.get('a'),               # TurkPrime metadata
        tp_a         = request.args.get('tp_a'),            # TurkPrime metadata
        b            = request.args.get('b'),               # TurkPrime metadata
        tp_b         = request.args.get('tp_b'),            # TurkPrime metadata
        c            = request.args.get('c'),               # TurkPrime metadata
        tp_c         = request.args.get('tp_c'),            # TurkPrime metadata
        address      = request.remote_addr,                 # NivTurk metadata
        browser      = request.user_agent.browser,          # User metadata
        platform     = request.user_agent.platform,         # User metadata
        version      = request.user_agent.version,          # User metadata
    )

    ## Case 1: workerId absent.
    if info['workerId'] is None:

        ## Redirect participant to error (missing workerId).
        return redirect(url_for('error.error', errornum=1000))

    ## Case 2: mobile user.
    elif info['platform'] in ['android','iphone','ipad','wii']:

        ## Redirect participant to error (platform error).
        return redirect(url_for('error.error', errornum=1001))

    ## Case 3: repeat visit, previous success.
    elif f"{info['subId']}.json" in os.listdir(data_dir):

        ## Update metadata.
        session['workerId'] = info['workerId']
        session['complete'] = 'success'

        ## Redirect participant to complete page.
        return redirect(url_for('complete.complete'))

    ## Case 4: repeat visit, previous reject.
    elif f"{info['subId']}.json" in os.listdir(reject_dir):

        ## Update metadata.
        session['workerId'] = info['workerId']
        session['complete'] = 'reject'

        ## Redirect participant to complete page.
        return redirect(url_for('complete.complete'))

    ## Case 5: repeat visit, preexisting log but no session data.
    elif not 'workerId' in session and info['workerId'] in os.listdir(meta_dir):

        ## Update metadata.
        for k, v in info.items(): session[k] = v
        session['WARNING'] = "Incognito user."
        write_metadata(session, ['subId','WARNING'], 'a')

        ## Redirect participant to consent form.
        return redirect(url_for('consent.consent'))

    ## Case 6: repeat visit, preexisting activity.
    elif 'workerId' in session:

        ## Update metadata.
        session['WARNING'] = "Revisited home."
        write_metadata(session, ['WARNING'], 'a')

        ## Redirect participant to consent form.
        return redirect(url_for('consent.consent'))

    ## Case 7: first visit, workerId present.
    else:

        ## Update metadata.
        for k, v in info.items(): session[k] = v
        write_metadata(session, ['workerId','hitId','assignmentId','subId','address','browser','platform','version'], 'w')

        ## Redirect participant to consent form.
        return redirect(url_for('consent.consent'))
