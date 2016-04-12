#
# A page showing all queued approvals and comments, as well as items
# that are ready for review.
#

class Queue < React
  def self.buttons()
    buttons = [{button: Refresh}]
    buttons << {form: Commit} if Pending.count > 0
    return buttons
  end

  def render
    _div.col_xs_12 do

      if Server.role == :director
        # Approvals
        _h4 'Approvals'
        _p.col_xs_12 do
          @approvals.each_with_index do |item, index|
            _span ', ' if index > 0
            _Link text: item.title, href: "queue/#{item.href}"
          end
          _em 'None.' if @approvals.empty?
        end

        # Unapproved
        %w(Unapprovals Flagged Unflagged).each do |section|
          list = self.state[section.downcase()]
          unless list.empty?
            _h4 section
            _p.col_xs_12 do
              list.each_with_index do |item, index|
                _span ', ' if index > 0
                _Link text: item.title, href: item.href
              end
            end
          end
        end
      end

      # Comments
      _h4 'Comments'
      if @comments.empty?
        _p.col_xs_12 {_em 'None.'} 
      else
        _dl.dl_horizontal(@comments) do |item|
          _dt do
            _Link text: item.title, href: item.href
          end
          _dd do
            item.pending.split("\n\n").each do |paragraph|
              _p paragraph
            end
          end
        end
      end

      # Action Item Status updates
      unless Pending.status.empty?
        _h4 'Action Items'
        _ul Pending.status do |item|
          text = item.text
          if item.pmc or item.date
            text += ' ['
            text += " #{item.pmc}" if item.pmc
            text += " #{item.date}" if item.date
            text += ' ]'
          end

          _li text
        end
      end

      # Ready
      if Server.role == :director and not @ready.empty?
        _div.row.col_xs_12 { _hr }

        _h4 'Ready for review'
        _p.col_xs_12 do
          @ready.each_with_index do |item, index|
            _span ', ' if index > 0
            _Link text: item.title, href: "queue/#{item.href}",
              class: ('default' if index == 0)
          end
        end
      end
    end
  end

  # set state on first load
  def componentWillMount()
    self.componentWillReceiveProps()
  end

  # determine approvals, rejected, comments, and ready
  def componentWillReceiveProps()
    @approvals = []
    @unapprovals = []
    @flagged = []
    @unflagged = []
    @comments = []
    @ready = []

    Agenda.index.each do |item|
      if Pending.comments[item.attach]
        @comments << item
      end

      action = false

      if Pending.approved.include? item.attach
        @approvals << item   
        action = true
      end

      if Pending.unapproved.include? item.attach
        @unapprovals << item 
        action = true
      end

      if Pending.flagged.include? item.attach
        @flagged << item     
        action = true
      end

      if Pending.unflagged.include? item.attach
        @unflagged << item   
        action = true
      end

      if not action and item.ready_for_review(Server.initials)
        @ready << item       
      end
    end
  end
end
