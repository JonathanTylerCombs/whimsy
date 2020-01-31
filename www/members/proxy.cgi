#!/usr/bin/env ruby
PAGETITLE = "Member Meeting Proxy Selection Form" # Wvisible:meeting
$LOAD_PATH.unshift '/srv/whimsy/lib'

require 'whimsy/asf'
require 'wunderbar'
require 'wunderbar/bootstrap'
require 'wunderbar/jquery'
require 'date'
require 'tmpdir'
require_relative 'meeting-util'

# TODO: Read in proxies between Volunteers: and Assignments: lines
volunteers = [
  "Shane Curcuru (curcuru)",
  "Craig L Russell (clr)"
]

# Emit basic instructions and details on quorum
def emit_instructions(today, cur_mtg_dir, meeting)
  if today > meeting
    _p.text_warning %{
        WARNING: Data for the next Member's Meeting is not yet available, 
        so this form will not work yet.  Please wait until the Chairman 
        announces the opening of nominations for the board and new members,
        and then check back to assign a new proxy for the meeting.
        Data from the previous meeting on #{meeting} is shown below for debugging only.
      }
  end
  _p %{
    This form allows you to assign an attendance proxy for the upcoming 
    Member's Meeting on #{meeting}. If there is any chance you might not be able 
    to attend the first part of the Member's Meeting on Tuesday in IRC, then 
    please assign a proxy, because that helps the meeting reach 
    quorum more quickly. 
    You can still attend the meeting if you want, and can revoke a 
    proxy at any time.
  }
  _p %{
    If you submit a proxy, you will still be sent board and new member ballots by email 
    during the meeting's 46 hour recess (between Tuesday and Thursday, 
    with two hours for vote counting), so you will still need to 
    cast your votes by checking your mail during the recess. If 
    you won't have internet access the week of the meeting, ask 
    for how to assign a proxy for your vote ballots as well.
  }
  num_members, quorum_need, num_proxies, attend_irc = MeetingUtil.calculate_quorum(cur_mtg_dir)
  if num_members
    _p do
      _ 'Currently, we must have '
      _span.text_primary "#{attend_irc}" 
      _ " Members attend the first half of the #{meeting} meeting and respond to Roll Call to reach quorum and continue the meeting."
      _ " Calculation: Total voting members: #{num_members}, with one third for quorum: #{quorum_need}, minus previously submitted proxies: #{num_proxies}"
    end
  end
end

# Emit meeting data and form for user to select a proxy - GET
def emit_form(cur_mtg_dir, meeting, volunteers)
  help, copypasta = MeetingUtil.is_user_proxied(cur_mtg_dir, $USER)
  user_is_proxy = help && copypasta
  _whimsy_panel(user_is_proxy ? "You Are Proxying For Others" : "Select A Proxy For Upcoming Meeting", style: 'panel-success') do
    _div do
      if help
        _p help
        if copypasta
          _ul.bg_success do
            copypasta.each do |copyline|
              _pre copyline
            end
          end
        end
      else
        _p 'The following members have volunteered to serve as proxies; you can freely select any one of them below:'
        _ul do
          volunteers.each do |vol|
            _pre vol
          end
        end
      end
    end
    
    if user_is_proxy
      _p.text_warning %{
          NOTE: you are proxying for other members, so you cannot assign 
          someone else to proxy for your attendance.  If it turns out that 
          you will not be able to attend the first half of the IRC meeting
          on Tuesday, you MUST work with the Chairman and your proxies 
          to update the proxy records, and get someone else to mark their presence!
        }
    else
      _div.well.well_lg do
        _form method: 'POST' do
          _div.form_group do
            _label 'Select proxy'
            
            # Fetch LDAP
            ldap_members = ASF.members
            ASF::Person.preload('cn', ldap_members)
            
            # Fetch members.txt
            members_txt = ASF::Member.list
            
            # get a list of members who have submitted proxies
            exclude = Dir[File.join(cur_mtg_dir,'proxies-received', '*')].
              map {|name| name[/(\w+)\.\w+$/, 1]}

            _select.combobox.input_large.form_control name: 'proxy' do
              _option 'Select an ASF Member', :selected, value: ''
              ldap_members.sort_by(&:public_name).each do |member|
                next if member.id == $USER               # No self proxies
                next if exclude.include? member.id       # Not attending
                next unless members_txt[member.id]       # Non-members
                next if members_txt[member.id]['status'] # Emeritus/Deceased
                # Display the availid to users to match volunteers array above
                _option "#{member.public_name} (#{member.id})"
              end
            end
          end
          _div_.form_group do
            _p do
              _ "IMPORTANT! Be sure to tell the person that you select as proxy above that you've assigned them to mark your attendance! They simply need to mark your proxy attendance when the meeting starts."
              _a 'Read full procedures for Member Meeting', href: 'https://www.apache.org/foundation/governance/members.html#meetings'
            end
            _div.button_group.text_center do
              _button.btn.btn_primary 'Submit'
            end
          end
        end
        _pre IO.read(File.join(cur_mtg_dir, 'member_proxy.txt').untaint)
      end
    end
  end
  
##    _script src: "js/jquery-1.11.1.min.js"
##    _script src: "js/bootstrap.min.js"
  _script src: "js/bootstrap-combobox.js" # TODO do we need this still?
  
  _script_ %{
    // convert select into combobox
    $('.combobox').combobox();
    
    // initially disable submit
    $('.btn').prop('disabled', true);
    
    // enable submit when proxy is chosen
    $('*[name="proxy"]').change(function() {
      $('.btn').prop('disabled', false);
      });
  }
end

# Emit a record of a user's submission - POST
def emit_post(cur_mtg_dir, meeting)
  _h3_ 'Proxy Assignment - Session Transcript'

  # collect data
  proxy = File.read(File.join(cur_mtg_dir, 'member_proxy.txt'))
  user = ASF::Person.find($USER)
  date = Date.today.strftime("%B %-d, %Y")

  # update proxy form (match as many _ as possible up to the name length)
  proxy[/authorize _(_{,#{@proxy.length}})/, 1] = @proxy.gsub(' ', '_')

  proxy[/signature: _(_#{'_' *user.public_name.length}_)/, 1] = 
    "/#{user.public_name.gsub(' ', '_')}/"

  proxy[/name: _(#{'_' *user.public_name.length})/, 1] = 
    user.public_name.gsub(' ', '_')

  proxy[/availid: _(#{'_' *user.id.length})/, 1] = 
    user.id.gsub(' ', '_')

  proxy[/Date: _(#{'_' *date.length})/, 1] = date.gsub(' ', '_')

  proxyform = proxy.untaint

  # report on commit
  _div.transcript do
    Dir.mktmpdir do |tmpdir|
      svn = `svn info #{MEETINGS}/#{meeting}`[/URL: (.*)/, 1]

      _.system [
        'svn', 'checkout', '--quiet', svn.untaint, tmpdir.untaint,
        ['--no-auth-cache', '--non-interactive'],
        (['--username', $USER, '--password', $PASSWORD] if $PASSWORD)
      ]

      Dir.chdir(tmpdir) do
        # write proxy form
        filename = "proxies-received/#$USER.txt".untaint
        File.write(filename, proxyform)
        _.system ['svn', 'add', filename]
        _.system ['svn', 'propset', 'svn:mime-type',
          'text/plain; charset=utf-8', filename]

        # get a list of proxies
        list = Dir['proxies-received/*.txt'].map do |file|
          form = File.read(file.untaint)
    
          id = file[/([-A-Za-z0-9]+)\.\w+$/, 1]
          proxy = form[/hereby authorize ([\S].*) to act/, 1].
            gsub('_', ' ').strip
          # Ensure availid is not included in proxy name here
          proxy = proxy[/([^(]+)/, 1].strip
          name = form[/signature: ([\S].*)/, 1].gsub(/[\/_]/, ' ').strip

          "   #{proxy.ljust(24)} #{name} (#{id})"
        end

        # gather a list of all non-text proxies (TODO unused)
        nontext = Dir['proxies-received/*'].
          reject {|file| file.end_with? '.txt'}.
          map {|file| file[/([-A-Za-z0-9]+)\.\w+$/, 1]}

        # update proxies file
        proxies = IO.read('proxies')
        existing = proxies.scan(/   \S.*\(\S+\).*$/)
        existing_ids = existing.map {|line| line[/\((\S+)\)/, 1] }
        added = list.
          reject {|line| existing_ids.include? line[/\((\S+)\)$/, 1]}
        list = added + existing
        proxies[/.*-\n(.*)/m, 1] = list.flatten.sort.join("\n") + "\n"

        IO.write('proxies', proxies)

        # commit
        _.system [
          'svn', 'commit', filename, 'proxies',
          '-m', "assign #{@proxy} as my proxy",
          ['--no-auth-cache', '--non-interactive'],
          (['--username', $USER, '--password', $PASSWORD] if $PASSWORD)
        ]
        # TODO: send email to @proxy per WHIMSY-78
      end
    end
  end
  
  # Report on contents now that they're checked in
  _h3! do
    _span "Contents of "
    _code "foundation/Meetings/#{meeting}/#{$USER}.txt"
    _span " as now checked in to svn:"
  end
  _pre proxyform
end

# produce HTML
_html do
  _style :system
  _style %{
    .transcript {margin: 0 16px}
    .transcript pre {border: none; line-height: 0}
  }
  _body? do
    # Find latest meeting and check if it's in the future yet
    MEETINGS = ASF::SVN['Meetings']
    cur_mtg_dir = MeetingUtil.get_latest(MEETINGS).untaint
    meeting = File.basename(cur_mtg_dir)
    today = Date.today.strftime('%Y%m%d')
    _whimsy_body(
      title: PAGETITLE,
      subtitle: today > meeting ? "ERROR: Next Meeting Data Not Available" : "How To Assign A Proxy For Upcoming Meeting",
      related: {
        '/members/meeting' => 'How-To / FAQ for Member Meetings',
        '/members/attendance-xcheck' => 'Members Meeting Attendance Crosscheck',
        '/members/inactive' => 'Inactive Member Feedback Form',
        '/members/subscriptions' => 'Members@ Mailing List Crosscheck'
      },
      helpblock: -> {
        emit_instructions(today, cur_mtg_dir, meeting)
      }
    ) do
      if _.get?
        emit_form(cur_mtg_dir, meeting, volunteers)
      else # POST
        emit_post(cur_mtg_dir, meeting)
      end
    end
  end
end

