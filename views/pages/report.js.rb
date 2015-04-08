#
# A two section representation of an agenda item (typically a PMC report),
# where the two sections will show up as two columns on wide enough windows.
#
# The first section contains the item text, with a missing indicator if
# the report isn't present.  It also contains an inline copy of draft
# minutes for agenda items in section 3.
#
# The second section contains posted comments, pending comments, and
# action items associated with this agenda item.
#
# Filters may be used to highlight or hypertext link portions of the text.
#

class Report < React
  def render
    _section.flexbox do
      _section do
        _pre.report do
          if @@item.missing
            _p {_em 'Missing'} 
          elsif @@item.text
            _Text raw: @@item.text, filters: @filters
          else
            _p {_em 'Empty'} 
          end
        end

        if @@item.minutes
          _pre.comment do
            _Text raw: @@item.minutes, filters: [hotlink]
          end
        end
      end

      _section do
        unless @@item.comments.empty?
          _h3.comments! 'Comments'
          @@item.comments.each do |comment|
            _pre.comment do
              _Text raw: comment, filters: [hotlink]
            end
          end
        end

        if @@item.pending
          _h3.comments! 'Pending Comment'
          _pre.comment "#{Pending.initials}: #{@@item.pending}"
        end

        if @@item.title != 'Action Items' and @@item.actions
          _h3.comments! { _Link text: 'Action Items', href: 'Action-Items' }
          @@item.actions.each do |action|
            _pre.comment action
          end
        end
      end
    end
  end

  # check for additional actions on initial render
  def componentWillMount()
    self.componentWillReceiveProps()
  end

  def componentWillReceiveProps()
    # determine what text filters to run
    @filters = [hotlink]
    @filters << self.localtime if @@item.title == 'Call to order'
    @filters << self.names if @@item.people

    # special processing for Minutes from previous meetings
    if @@item.attach =~ /^3[A-Z]$/
      @filters = [self.linkMinutes]

      # if draft is available, fetch minutes for display
      date = @@item.text[/board_minutes_(\d+_\d+_\d+)\.txt/, 1]

      if 
        date and not defined? @@item.minutes and defined? XMLHttpRequest and
        Server.drafts.include? "board_minutes_#{date}.txt"
      then
        @@item.minutes = ''
        fetch "minutes/#{date}", :text do |minutes|
          @@item.minutes = minutes
          Main.refresh()
        end
      end
    end
  end

  #
  ### filters
  #

  # Convert start time to local time on Call to order page
  def localtime(text)
    return text.sub /\n(\s+)(Other Time Zones:.*)/ do |match, spaces, text|
      localtime = Date.new(@@item.timestamp).toLocaleString()
      "\n#{spaces}<span class='hilite'>" +
        "Local Time: #{localtime}</span>#{spaces}#{text}"
    end
  end

  # replace ids with committer links
  def names(text)
    roster = 'https://whimsy.apache.org/roster/committer/'

    for id in @@item.people
      person = @@item.people[id]

      # email addresses in 'Establish' resolutions
      text.gsub! /(\(|&lt;)(#{id})( at |@|\))/ do |m, pre, id, post|
        if person.icla
          "#{pre}<a href='#{roster}#{id}'>#{id}</a>#{post}"
        else
          "#{pre}<a class='missing' href='#{roster}?q=#{person.name}'>" +
            "#{id}</a>#{post}"
        end
      end

      # names
      if person.icla or @@item.title == 'Roll Call'
        if defined? person.member
          text.sub! /#{escapeRegExp(person.name)}/, 
            "<a href='#{roster}#{id}'>#{person.name}</a>"
        else
          text.sub! /#{escapeRegExp(person.name)}/, 
            "<a href='#{roster}?q=#{person.name}'>#{person.name}</a>"
        end
      end

      # highlight potentially misspelled names
      if person.icla and not person.icla == person.name
        names = person.name.split(/\s+/)
        iclas = person.icla.split(/\s+/)
        ok = false
        ok ||= names.all? {|part| iclas.any? {|icla| icla.include? part}}
        ok ||= iclas.all? {|part| names.any? {|name| name.include? part}}
        if @@item.title =~ /^Establish/ and not ok
          text.gsub! /#{escapeRegExp("#{id}'>#{person.name}")}/,
            "?q=#{encodeURIComponent(person.name)}'>" +
            "<span class='commented'>#{person.name}</span>"
        else
          text.gsub! /#{escapeRegExp(person.name)}/, 
            "<a href='#{roster}#{id}'>#{person.name}</a>"
        end
      end

      # put members names in bold
      if person.member
        text.gsub! /#{escapeRegExp(person.name)}/, "<b>#{person.name}</b>"
      end
    end

    # treat any unmatched names in Roll Call as misspelled
    if @@item.title == 'Roll Call'
      text.gsub! /(\n\s{4})([A-Z].*)/ do |match, space, name|
        "#{space}<a class='commented' href='#{roster}?q=#{name}'>#{name}</a>"
      end
    end

    return text
  end

  # link to board minutes
  def linkMinutes(text)
    text.gsub! /board_minutes_(\d+)_\d+_\d+\.txt/ do |match, year|
      if Server.drafts.include? match
        link = "https://svn.apache.org/repos/private/foundation/board/#{match}"
      else
        link = "http://apache.org/foundation/records/minutes/#{year}/#{match}"
      end
      "<a href='#{link}'>#{match}</a>"
    end

    return text
  end
end
