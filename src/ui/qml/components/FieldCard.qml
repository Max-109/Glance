import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var theme
    property string title: ""
    property string description: ""
    default property alias contentData: contentColumn.data

    Layout.fillWidth: true
    implicitWidth: 620
    radius: 14
    color: theme.surfaceRaisedStronger
    border.width: 1
    border.color: theme.borderWeakBase

    ColumnLayout {
        id: cardColumn
        anchors.fill: parent
        anchors.margins: 20
        spacing: 18

        ColumnLayout {
            spacing: 4
            Layout.fillWidth: true

            Text {
                text: root.title
                color: theme.textStrong
                font.pixelSize: 16
                font.weight: 500
                wrapMode: Text.Wrap
            }

            Text {
                visible: root.description.length > 0
                text: root.description
                color: theme.textBase
                font.pixelSize: 14
                font.weight: 400
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }

        ColumnLayout {
            id: contentColumn
            spacing: 14
            Layout.fillWidth: true
        }
    }

    implicitHeight: cardColumn.implicitHeight + 36
}
